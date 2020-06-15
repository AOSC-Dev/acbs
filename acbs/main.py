import logging
import logging.handlers
import traceback
import sys
import os

from acbs.utils import invoke_autobuild, guess_subdir, full_line_banner, print_package_names, make_build_dir, ACBSLogFormatter
from acbs.parser import get_tree_by_name, get_deps_graph
from acbs.find import find_package, check_package_groups, expand_package_group
from acbs.deps import tarjan_search
from acbs.fetch import fetch_source, process_source
from acbs.pm import install_from_repo
from acbs.const import CONF_DIR, DUMP_DIR, TMP_DIR, LOG_DIR
from acbs import __version__


class BuildCore(object):

    def __init__(self, args) -> None:
        self.debug = args.debug
        self.no_deps = args.no_deps
        self.dl_only = args.get
        self.tree = args.acbs_tree or 'default'
        self.build_queue = args.packages
        self.tree_dir = ''
        # static vars
        self.conf_dir = CONF_DIR
        self.dump_dir = DUMP_DIR
        self.tmp_dir = TMP_DIR
        self.log_dir = LOG_DIR
        self.init()

    def init(self) -> None:
        sys.excepthook = self.acbs_except_hdr
        print(full_line_banner(
            'Welcome to ACBS - {}'.format(__version__)))
        if self.debug:
            log_verbosity = logging.DEBUG
        else:
            log_verbosity = logging.INFO
        try:
            for directory in [self.dump_dir, self.tmp_dir, self.conf_dir,
                              self.log_dir]:
                if not os.path.isdir(directory):
                    os.makedirs(directory)
        except Exception:
            raise IOError('\033[93mFailed to create work directories\033[0m!')
        self.__install_logger(log_verbosity)
        forest_file = os.path.join(self.conf_dir, 'forest.conf')
        if os.path.exists(forest_file):
            self.tree_dir = get_tree_by_name(forest_file, self.tree)
            if not self.tree_dir:
                raise ValueError('Tree not found!')
        else:
            raise Exception('forest.conf not found')

    def __install_logger(self, str_verbosity=logging.INFO,
                         file_verbosity=logging.DEBUG):
        logger = logging.getLogger()
        logger.setLevel(0)  # Set to lowest to bypass the initial filter
        str_handler = logging.StreamHandler()
        str_handler.setLevel(str_verbosity)
        str_handler.setFormatter(ACBSLogFormatter())
        logger.addHandler(str_handler)
        log_file_handler = logging.handlers.RotatingFileHandler(
            os.path.join(self.log_dir, 'acbs-build.log'), mode='a', maxBytes=2e5, backupCount=3)
        log_file_handler.setLevel(file_verbosity)
        log_file_handler.setFormatter(logging.Formatter(
            '%(asctime)s:%(levelname)s:%(message)s'))
        logger.addHandler(log_file_handler)

    def build(self) -> None:
        packages = []
        error = False
        # begin finding and resolving dependencies
        logging.info('Searching and resolving dependencies...')
        for i in self.build_queue:
            logging.debug('Finding {}...'.format(i))
            package = find_package(i, self.tree_dir)
            if not package:
                raise RuntimeError('Could not find package {}'.format(i))
            packages.extend(package)
        if not self.no_deps:
            logging.debug('Converting queue into adjacency graph...')
            graph = get_deps_graph(packages)
            logging.debug('Running Tarjan search...')
            resolved = tarjan_search(graph, self.tree_dir)
        else:
            logging.warning('Warning: Dependency resolution disabled!')
            resolved = [[package] for package in packages]
        # print a newline
        print()
        packages.clear()  # clear package list for the search results
        # here we will check if there is any loop in the dependency graph
        for dep in resolved:
            if len(dep) > 1:
                # this is a SCC, aka a loop
                logging.error('Found a loop in the dependency graph: {}'.format(
                    print_package_names(dep)))
                error = True
            elif not error:
                packages.extend(dep)
        if error:
            raise RuntimeError(
                'Dependencies NOT resolved. Couldn\'t continue!')
        check_package_groups(packages)
        logging.info(
            'Dependencies resolved, {} packages in the queue'.format(len(resolved)))
        logging.debug('Queue: {}'.format(packages))
        logging.info('Packages to be built: {}'.format(
            print_package_names(packages, 5)))
        # build process
        for task in packages:
            logging.info('Building {}...'.format(task.name))
            fetch_source(task.source_uri, self.dump_dir, task.name)
            if not task.build_location or not os.path.exists(task.build_location):
                build_dir = make_build_dir(self.tmp_dir)
                task.build_location = build_dir
                process_source(task)
            if task.source_uri.subdir:
                build_dir = os.path.join(build_dir, task.source_uri.subdir)
            else:
                subdir = guess_subdir(build_dir)
                if not subdir:
                    raise RuntimeError(
                        'Could not determine sub-directory, please specify manually.')
                build_dir = os.path.join(build_dir, subdir)
            install_from_repo(task.installables)
            invoke_autobuild(task, build_dir)

    def acbs_except_hdr(self, type, value, tb):
        logging.debug('Traceback:\n' + ''.join(traceback.format_tb(tb)))
        if self.debug:
            sys.__excepthook__(type, value, tb)
        else:
            print()
            logging.fatal('Oops! \033[93m%s\033[0m: \033[93m%s\033[0m' % (
                str(type.__name__), str(value)))
