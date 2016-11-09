import logging
import logging.handlers
import os
import sys
import traceback

from lib.acbs_find import acbs_find
from lib.acbs_utils import acbs_utils, ACBSGeneralError, acbs_log_format, ACBSConfError
from lib.acbs_parser import acbs_parser, ACBSPackgeInfo
from lib.acbs_src_fetch import acbs_src_fetch
from lib.acbs_misc import acbs_misc
from lib.acbs_src_process import acbs_src_process
# from acbs_const import acbs_const
from lib.acbs_start_build import acbs_start_ab
from lib.acbs_deps import acbs_deps


class acbs_build_core(object):

    def __init__(self, pkgs_name, debug_mode=False, tree='default', version='?', init=True):
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
        self.acbs_version = version
        self.tree_loc = None
        self.acbs_settings = {'debug_mode': self.isdebug, 'tree': self.tree,
                              'version': self.acbs_version}
        if init:
            self.init()

    def init(self):
        sys.excepthook = self.acbs_except_hdr
        print(acbs_utils.full_line_banner(
            'Welcome to ACBS - {}'.format(self.acbs_version)))
        if self.isdebug:
            str_verbosity = logging.DEBUG
        else:
            str_verbosity = logging.INFO
        self.__install_logger(str_verbosity)
        try:
            for dir_loc in [self.dump_loc, self.tmp_loc, self.conf_loc,
                            self.log_loc]:
                if not os.path.isdir(dir_loc):
                    os.makedirs(dir_loc)
        except:
            raise IOError('\033[93mFailed to make work directory\033[0m!')
        acbs_misc().dev_utilz_warn()
        if os.path.exists(os.path.join(self.conf_loc, 'forest.conf')):
            self.tree_loc = acbs_parser(
                main_data=self).parse_acbs_conf(self.tree)
            if not self.tree_loc:
                raise ACBSConfError('Tree not found!')
        else:
            acbs_parser(main_data=self).write_acbs_conf()
        return

    def __install_logger(self, str_verbosity=logging.INFO,
                         file_verbosity=logging.DEBUG):
        logger = logging.getLogger()
        logger.setLevel(str_verbosity)
        str_handler = logging.StreamHandler()
        str_handler.setLevel(str_verbosity)
        str_handler.setFormatter(acbs_log_format())
        logger.addHandler(str_handler)
        log_file_handler = logging.handlers.RotatingFileHandler(
            os.path.join(self.log_loc, 'acbs-build.log'), mode='a', maxBytes=2e5, backupCount=10)
        log_file_handler.setLevel(file_verbosity)
        log_file_handler.setFormatter(logging.Formatter(
            '%(asctime)s:%(levelname)s:%(message)s'))
        logger.addHandler(log_file_handler)
        return

    def build(self, pkgs=None):
        pkgs_to_build = pkgs or self.pkgs_name
        for pkg in pkgs_to_build:
            matched_pkg = acbs_find(
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

    def build_pkg_group(self):
        pass
        return

    def build_single_pkg(self, single_pkg):
        logging.info('Start building \033[36m{}\033[0m'.format(single_pkg))
        os.chdir(self.tree_loc)
        self.pkg_data.slug = single_pkg
        pkg_type_res = acbs_find.determine_pkg_type(single_pkg)
        if isinstance(pkg_type_res, dict):
            pkgs_array = pkg_type_res
            pkg_tuple = [(lambda x, y, z: (y, '%s/0%s-%s' % (z, x, y)) if x < 10 else (y, '%s/%s-%s' %
                                                                                       (z, str(x), y)))(i, pkgs_array[i], single_pkg) for i in pkgs_array]
            logging.info('Package group detected\033[36m({})\033[0m: contains: \033[36m{}\033[0m'.format(
                len(pkg_tuple), ' '.join([i[0] for i in pkg_tuple])))
            logging.debug('Package group building order: {}'.format(pkgs_array))
            raise NotImplementedError('Sub packages building not implemented')
            # return build_sub_pkgs(single_pkg, pkg_type_res)  # FIXME
        try:
            pkg_slug = os.path.basename(single_pkg)
        except:
            pkg_slug = single_pkg
            self.pkg_data.name = pkg_slug
        parser = acbs_parser(
            pkg_name=pkg_slug, spec_file_loc=os.path.abspath(single_pkg))
        self.pkg_data.update(parser.parse_abbs_spec())
        repo_dir = os.path.abspath(single_pkg)
        self.pkg_data.update(parser.parse_ab3_defines(
            os.path.join(single_pkg, 'autobuild/defines')))
        try_build = acbs_deps().process_deps(
            self.pkg_data.build_deps, self.pkg_data.run_deps, pkg_slug)
        if try_build:
            if try_build in self.pending_pkgs:
                # Suspect this is dependency loop
                raise ACBSGeneralError('Dependency loop: {}'.format(
                    '->'.join(list(self.pending_pkgs + try_build))))
            self.new_build_thread(try_build)
        src_fetcher = acbs_src_fetch(
            self.pkg_data.buffer['abbs_data'], self.dump_loc)
        self.pkg_data.src_name = src_fetcher.fetch_src()
        self.pkg_data.src_path = self.dump_loc
        tmp_dir_loc = acbs_src_process(self.pkg_data, self).process()
        repo_ab_dir = os.path.join(repo_dir, 'autobuild/')
        ab3 = acbs_start_ab(tmp_dir_loc, repo_ab_dir, self.pkg_data)
        ab3.copy_abd()
        ab3.timed_start_ab3()
        self.pkgs_que.discard(single_pkg)
        return 0

    def new_build_thread(self, try_build):
        def slave_thread_build(pkg):
            logging.debug(
                'New build thread started for \033[36m{}\033[0m'.format(pkg))
            new_build_instance = acbs_build_core(
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
