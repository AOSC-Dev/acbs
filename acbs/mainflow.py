import logging
import logging.handlers
import os
import sys
import traceback

from acbs.find import Finder
from acbs import utils
from acbs.utils import ACBSGeneralError, ACBSConfError
from acbs.parser import ACBSPackageGroup, write_acbs_conf, parse_acbs_conf
from acbs.src_fetch import SourceFetcher
from acbs.misc import Misc, Fortune
from acbs.src_process import SourceProcessor
from acbs.loader import LoaderHelper
from acbs.utils import ACBSVariables
from acbs.start_build import Autobuild
from acbs.deps import Dependencies


class BuildCore(object):

    def __init__(self, pkgs_name, debug_mode=False, tree='default', version='', init=True, syslog=False, download_only=False, pending=None):
        '''
        '''
        self.pkgs_name = pkgs_name
        self.isdebug = debug_mode
        self.tree = tree
        self.pkgs_que = set()
        self.pkgs_done = []
        self.dump_loc = '/var/cache/acbs/tarballs/'
        self.tmp_loc = '/var/cache/acbs/build/'
        self.conf_loc = '/etc/acbs/'
        self.log_loc = '/var/log/acbs/'
        self.acbs_version = version
        self.tree_loc = None
        self.log_to_system = syslog
        self.shared_error = None
        self.download_only = download_only
        self.pending = pending or ()
        self.acbs_settings = {'debug_mode': self.isdebug, 'tree': self.tree,
                              'version': self.acbs_version}
        if init:
            self.init()

    def init(self):
        sys.excepthook = self.acbs_except_hdr
        print(utils.full_line_banner(
            'Welcome to ACBS - {}'.format(self.acbs_version), '='))
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
        forest_file = os.path.join(self.conf_loc, 'forest.conf')
        if os.path.exists(os.path.join(self.conf_loc, 'forest.conf')):
            self.tree_loc = os.path.abspath(parse_acbs_conf(forest_file, self.tree))
            if not self.tree_loc:
                raise ACBSConfError('Tree not found!')
        else:
            self.tree_loc = os.path.abspath(write_acbs_conf(forest_file))

        # @LoaderHelper.register('after_build_finish')
        # def fortune():
        #     Fortune().get_comment()

        LoaderHelper.callback('after_init')

    def __install_logger(self, str_verbosity=logging.INFO,
                         file_verbosity=logging.DEBUG):
        logger = logging.getLogger()
        logger.setLevel(0)  # Set to lowest to bypass the initial filter
        str_handler = logging.StreamHandler()
        str_handler.setLevel(str_verbosity)
        str_handler.setFormatter(utils.ACBSColorFormatter(
            '[%(colorlevelname)s] %(message)s'))
        logger.addHandler(str_handler)
        if self.log_to_system:
            log_file_handler = logging.handlers.SysLogHandler(
                address='/dev/log')
        else:
            log_file_handler = logging.handlers.RotatingFileHandler(
                os.path.join(self.log_loc, 'acbs-build.log'), mode='a',
                maxBytes=2e5, backupCount=10)
        log_file_handler.setLevel(file_verbosity)
        log_file_handler.setFormatter(utils.ACBSTextLogFormatter(
            '%(asctime)s:%(levelname)s:%(message)s'))
        logger.addHandler(log_file_handler)

    def build(self):
        LoaderHelper.callback('before_build_init')
        pkgs_to_build = []
        for pkg in self.pkgs_name:
            matched_pkg = Finder(
                pkg, search_path=self.tree_loc).acbs_pkg_match()
            if isinstance(matched_pkg, list):
                logging.info('Package build list found: \033[36m%s (%s)\033[0m' %
                             (os.path.basename(pkg), len(matched_pkg)))
                pkgs_to_build.extend(matched_pkg)
            elif not matched_pkg:
                raise ACBSGeneralError(
                    'No valid candidate package found for %s.' %
                    utils.format_packages(pkg))
            else:
                pkgs_to_build.append(matched_pkg)
        for pkg in pkgs_to_build:
            self.pkgs_que.update(pkg)
            self.build_pkg_group(pkg)
        print(utils.full_line_banner('Build Summary:', '='))
        self.print_summary()
        LoaderHelper.callback('after_build_finish')
        return 0

    def print_summary(self):
        i = 0
        group_name = None
        prev_group_name = None
        accum = 0.0

        def swap_vars(prev_group_name):
            ACBSVariables.get('timings').insert(i, accum)
            self.pkgs_done.insert(i, prev_group_name)
            prev_group_name = group_name

        for it in self.pkgs_done:
            if it.find('::') > -1:
                group_name, sub_name = it.split('::')
                if prev_group_name and (group_name != prev_group_name):
                    swap_vars(prev_group_name)
                if sub_name == 'autobuild':
                    self.pkgs_done.remove(it)
                else:
                    accum += ACBSVariables.get('timings')[i]
                i += 1
        if group_name:
            swap_vars(group_name)        
        if self.download_only:
            x = [[name, 'Downloaded'] for name in self.pkgs_done]
        else:
            x = [[name, utils.human_time(time)] for name, time in zip(
                self.pkgs_done, ACBSVariables.get('timings'))]
        print(utils.format_column(x))
        return

    def build_main(self, pkg_data):
        # , target, tmp_dir_loc=[], skipbuild=False, groupname=None
        skipbuild = self.download_only
        pkg_name = pkg_data.pkg_name
        if not skipbuild:
            try_build = Dependencies().process_deps(
                pkg_data.build_deps, pkg_data.run_deps, pkg_name)
            if try_build:
                logging.info('Dependencies to build: ' +
                    utils.format_packages(try_build))
                if set(try_build).intersection(self.pending):
                    # Suspect this is dependency loop
                    err_msg = 'Dependency loop: %s' % '<->'.join(self.pending)
                    utils.err_msg(err_msg)
                    raise ACBSGeneralError(err_msg)
                self.new_build_thread(pkg_name, try_build)
        repo_ab_dir = pkg_data.ab_dir()
        if not skipbuild:
            ab3 = Autobuild(pkg_data.temp_dir, repo_ab_dir, pkg_data)
            ab3.copy_abd()
            ab3.timed_start_ab3()
        self.pkgs_done.append(
            pkg_data.directory if pkg_data.subdir != 'autobuild'
            else '%s::%s' % (pkg_data.directory, pkg_data.subdir))

    def build_pkg_group(self, directory):
        logging.info('Start building ' + utils.format_packages(directory))
        os.chdir(self.tree_loc)
        pkg_group = ACBSPackageGroup(directory, rootpath=self.tree_loc)
        #pkg_type_res = Finder.determine_pkg_type(directory)
        #if isinstance(pkg_type_res, dict):
            #return self.build_pkg_group1(pkg_type_res, directory)  # FIXME
        logging.info('Downloading sources...')
        src_fetcher = SourceFetcher(
            pkg_group.pkg_name, pkg_group.abbs_data, self.dump_loc)
        pkg_group.src_name = src_fetcher.fetch_src()
        pkg_group.src_path = self.dump_loc
        pkg_group.temp_dir = SourceProcessor(
            pkg_group, self.dump_loc, self.tmp_loc).process()
        subpkgs = pkg_group.subpackages()
        isgroup = (len(subpkgs) > 1)
        if isgroup:
            logging.info('Package group\033[36m({})\033[0m detected: '
                'contains: {}'.format(
                len(subpkgs), utils.format_packages(p.pkg_name for p in subpkgs)))
        for pkg_data in subpkgs:
            print(utils.full_line_banner('%s::%s' % (directory, pkg_data.pkg_name)))
            self.build_main(pkg_data)
        return 0

    def new_build_thread(self, current_pkg, try_build):
        def slave_thread_build(pkg, shared_error):
            logging.debug(
                'New build thread started for ' + utils.format_packages(pkg))
            try:
                new_build_instance = BuildCore(
                    **self.acbs_settings, pkgs_name=[pkg], init=False,
                    pending=self.pending + (current_pkg,))
                new_build_instance.tree_loc = self.tree_loc
                new_build_instance.shared_error = shared_error
                new_build_instance.build()
            except Exception as ex:
                shared_error.set()
                raise
            return
        from multiprocessing import Process, Event, Lock
        self.shared_error = Event()
        for sub_pkg in list(try_build):
            dumb_mutex = Lock()
            dumb_mutex.acquire()
            sub_thread = Process(
                target=slave_thread_build, args=(sub_pkg, self.shared_error))
            sub_thread.start()
            sub_thread.join()
            dumb_mutex.release()
            if self.shared_error.is_set():
                raise ACBSGeneralError(
                    'Sub-build process building {} \033[93mfailed!\033[0m'.format(
                    utils.format_packages(sub_pkg)))

    def acbs_except_hdr(self, type, value, tb):
        if self.isdebug:
            sys.__excepthook__(type, value, tb)
        else:
            print()
            logging.fatal('Oops! \033[93m%s\033[0m: %s' % (
                str(type.__name__), str(value)))
        logging.error('Traceback:\n' + ''.join(traceback.format_tb(tb)))
