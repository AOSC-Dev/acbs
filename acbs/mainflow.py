import logging
import logging.handlers
import os
import sys
import traceback

from acbs.find import Finder
from acbs import utils
from acbs.utils import ACBSGeneralError, ACBSLogFormatter, ACBSConfError
from acbs.parser import Parser, ACBSPackgeInfo
from acbs.src_fetch import SourceFetcher
from acbs.misc import Misc
from acbs.src_process import SourceProcessor
# from acbs import const
from acbs.start_build import Autobuild
from acbs.deps import Dependencies


class BuildCore(object):

    def __init__(self, pkgs_name, debug_mode=False, tree='default', version='?', init=True, syslog=False):
        '''
        '''
        self.pkgs_name = pkgs_name
        self.isdebug = debug_mode
        self.tree = tree
        self.pkgs_que = set()
        self.pending_pkgs = set()
        self.dump_loc = '/var/cache/acbs/tarballs/'
        self.tmp_loc = '/var/cache/acbs/build/'
        self.conf_loc = '/etc/acbs/'
        self.log_loc = '/var/log/acbs/'
        self.pkg_data = ACBSPackgeInfo()
        self.isgroup = False
        self.acbs_version = version
        self.tree_loc = None
        self.log_to_system = syslog
        self.acbs_settings = {'debug_mode': self.isdebug, 'tree': self.tree,
                              'version': self.acbs_version}
        if init:
            self.init()

    def init(self):
        sys.excepthook = self.acbs_except_hdr
        print(utils.full_line_banner(
            'Welcome to ACBS - {}'.format(self.acbs_version)))
        if self.isdebug:
            str_verbosity = logging.DEBUG
        else:
            str_verbosity = logging.INFO
        try:
            for dir_loc in [self.dump_loc, self.tmp_loc, self.conf_loc,
                            self.log_loc]:
                if not os.path.isdir(dir_loc):
                    os.makedirs(dir_loc)
        except Exception:
            raise IOError('\033[93mFailed to make work directory\033[0m!')
        self.__install_logger(str_verbosity)
        Misc().dev_utilz_warn()
        if os.path.exists(os.path.join(self.conf_loc, 'forest.conf')):
            self.tree_loc = Parser(
                main_data=self).parse_acbs_conf(self.tree)
            if not self.tree_loc:
                raise ACBSConfError('Tree not found!')
        else:
            Parser(main_data=self).write_acbs_conf()

    def __install_logger(self, str_verbosity=logging.INFO,
                         file_verbosity=logging.DEBUG):
        logger = logging.getLogger()
        logger.setLevel(str_verbosity)
        str_handler = logging.StreamHandler()
        str_handler.setLevel(str_verbosity)
        str_handler.setFormatter(ACBSLogFormatter())
        logger.addHandler(str_handler)
        if self.log_to_system:
            log_file_handler = logging.handlers.SysLogHandler(
                address='/dev/log')
        else:
            log_file_handler = logging.handlers.RotatingFileHandler(
                os.path.join(self.log_loc, 'acbs-build.log'), mode='a', maxBytes=2e5, backupCount=10)
        log_file_handler.setLevel(file_verbosity)
        log_file_handler.setFormatter(logging.Formatter(
            '%(asctime)s:%(levelname)s:%(message)s'))
        logger.addHandler(log_file_handler)

    def build(self, pkgs=None):
        pkgs_to_build = pkgs or self.pkgs_name
        for pkg in pkgs_to_build:
            matched_pkg = Finder(
                pkg, search_path=self.tree_loc).acbs_pkg_match()
            if isinstance(matched_pkg, list):
                logging.info('Package build list found: \033[36m%s (%s)\033[0m' %
                             (os.path.basename(pkg), len(matched_pkg)))
                self.pkgs_name.remove(pkg)
                self.pkgs_name += matched_pkg
                return self.build()
            if not matched_pkg:
                raise ACBSGeneralError(
                    'No valid candidate package found for \033[36m%s\033[0m.' % pkg)
            else:
                self.pkgs_que.update(matched_pkg)
                self.build_single_pkg(matched_pkg)
        return 0

    def build_pkg_group(self, pkgs_array, single_pkg):
        self.isgroup = True
        self.pkgs_que.discard(single_pkg)
        import collections
        pkgs_array = collections.OrderedDict(
            sorted(pkgs_array.items(), key=lambda x: x[0]))
        pkg_tuple = [(lambda x, y, z: (y, '%s/0%s-%s' % (z, x, y)) if x < 10 else (y, '%s/%s-%s' %
                                                                                   (z, str(x), y)))(i, pkgs_array[i], single_pkg) for i in pkgs_array]
        logging.info('Package group detected\033[36m({})\033[0m: contains: \033[36m{}\033[0m'.format(
            len(pkg_tuple), ' '.join([i[0] for i in pkg_tuple])))
        logging.debug('Package group building order: {}'.format(pkgs_array))
        tmp_dir_loc = []
        self.build_main(single_pkg, tmp_dir_loc, skipbuild=True)
        for pkg_name, pkg_dir in pkg_tuple:
            print(utils.full_line_banner(''))
            logging.info('Start building \033[36m%s::%s\033[0m' % (
                single_pkg, pkg_name))
            self.pkg_data.clear()
            self.build_main(pkg_dir, tmp_dir_loc)

    def build_main(self, target, tmp_dir_loc=[], skipbuild=False):
        try:
            pkg_slug = os.path.basename(target)
        except Exception:
            pkg_slug = target
            self.pkg_data.name = pkg_slug
        parser = Parser(
            pkg_name=pkg_slug, spec_file_loc=os.path.abspath(target))
        if not tmp_dir_loc:
            self.pkg_data.update(parser.parse_abbs_spec())
        repo_dir = os.path.abspath(target)
        if not skipbuild:
            defines_loc = 'defines' if self.isgroup else 'autobuild/defines'
            self.pkg_data.update(parser.parse_ab3_defines(
                os.path.join(target, defines_loc)))
            try_build = Dependencies().process_deps(
                self.pkg_data.build_deps, self.pkg_data.run_deps, pkg_slug)
            if try_build:
                if try_build in self.pending_pkgs:
                    # Suspect this is dependency loop
                    raise ACBSGeneralError('Dependency loop: {}'.format(
                        '->'.join(list(self.pending_pkgs + try_build))))
                self.new_build_thread(try_build)
        src_fetcher = SourceFetcher(
            self.pkg_data.buffer['abbs_data'], self.dump_loc)
        self.pkg_data.src_name = src_fetcher.fetch_src()
        self.pkg_data.src_path = self.dump_loc
        if not tmp_dir_loc:
            tmp_dir_loc.append(SourceProcessor(self.pkg_data, self).process())
        repo_ab_dir = os.path.join(repo_dir, 'autobuild/')
        if not skipbuild:
            ab3 = Autobuild(tmp_dir_loc[0], repo_ab_dir, self.pkg_data)
            ab3.copy_abd()
            ab3.timed_start_ab3(rm_abdir=self.isgroup)
        self.pkgs_que.discard(target)

    def build_single_pkg(self, single_pkg):
        logging.info('Start building \033[36m{}\033[0m'.format(single_pkg))
        os.chdir(self.tree_loc)
        self.pkg_data.slug = single_pkg
        pkg_type_res = Finder.determine_pkg_type(single_pkg)
        if isinstance(pkg_type_res, dict):
            return self.build_pkg_group(pkg_type_res, single_pkg)  # FIXME
        self.build_main(single_pkg)
        return 0

    def new_build_thread(self, try_build):
        def slave_thread_build(pkg):
            logging.debug(
                'New build thread started for \033[36m{}\033[0m'.format(pkg))
            new_build_instance = BuildCore(
                **self.acbs_settings, pkgs_name=[pkg], init=False)
            new_build_instance.tree_loc = self.tree_loc
            return new_build_instance.build()
        from multiprocessing import pool
        from multiprocessing.pool import ThreadPool
        for sub_pkg in list(try_build):
            dumb_mutex = pool.threading.Lock()
            dumb_mutex.acquire()
            fake_pool = ThreadPool(processes=1)
            try:
                sub_thread = fake_pool.apply_async(
                    func=slave_thread_build, args=([sub_pkg]))
                dumb_mutex.release()
                return sub_thread.get()
            except Exception as ex:
                raise ACBSGeneralError(
                    'Sub-build process building \033[36m{}\033[0m \033[93mfailed!\033[0m'.format(sub_pkg)) from ex

    def acbs_except_hdr(self, type, value, tb):
        logging.debug('Traceback:\n' + ''.join(traceback.format_tb(tb)))
        if self.isdebug:
            sys.__excepthook__(type, value, tb)
        else:
            print()
            logging.fatal('Oops! \033[93m%s\033[0m: \033[93m%s\033[0m' % (
                str(type.__name__), str(value)))
