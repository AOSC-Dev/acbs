import logging
import logging.handlers
import os

from acbs_find import acbs_find
from acbs_utils import acbs_utils
from acbs_parser import acbs_parser
from acbs_src_fetch import acbs_src_fetch
from acbs_misc import acbs_misc
# from acbs_const import acbs_const
from acbs_start_build import acbs_start_ab
from acbs_deps import acbs_deps


class acbs_core_build(acbs_find, acbs_parser, acbs_src_fetch, acbs_start_ab, acbs_deps, acbs_misc):
    acbs_verion = '0.0.1-preview0'

    def __init__(self, pkgs_name, debug_mode=False, tree='default'):
        self.pkgs_name = pkgs_name
        self.isdebug = debug_mode
        self.tree = tree
        self.dump_loc = '/var/cache/acbs/tarballs/'
        self.tmp_loc = '/var/cache/acbs/build/'
        self.conf_loc = '/etc/acbs/'
        self.log_loc = '/var/log/acbs/'
        print(acbs_utils.full_line_banner(
            'Welcome to ACBS - {}'.format(self.acbs_version)))
        try:
            for dir_loc in [self.dump_loc, self.tmp_loc, self.conf_loc,
                            self.log_loc]:
                if not os.path.isdir(dir_loc):
                    os.makedirs(dir_loc)
        except:
            raise IOError('\033[93mFailed to make work directory\033[0m!')
        if self.isdebug:
            str_verbosity = logging.DEBUG
        else:
            str_verbosity = logging.INFO
        self.__install_logger(str_verbosity)
        acbs_misc().dev_utilz_warn()
        if os.path.exists(os.path.join(self.conf_loc, 'forest.conf')):
            tree_loc = acbs_parser.parse_acbs_conf(self.tree)
            if tree_loc is not None:
                os.chdir(tree_loc)
            else:
                raise acbs_utils.ACBSConfError('Tree not found!')
        else:
            if not acbs_parser.write_acbs_conf():
                raise acbs_utils.ACBSConfError('Failed to write configuration')
        return

    def __install_logger(self, str_verbosity=logging.INFO,
                         file_verbosity=logging.DEBUG):
        logger = logging.getLogger()
        logger.setLevel(str_verbosity)
        str_handler = logging.StreamHandler()
        str_handler.setLevel(logging.INFO)
        str_handler.setFormatter(acbs_utils.acbs_log_format())
        logger.addHandler(str_handler)
        log_file_handler = logging.handlers.RotatingFileHandler(
            os.path.join(self.log_loc, 'acbs-build.log'), mode='a', maxBytes=5120, backupCount=10)
        log_file_handler.setLevel(file_verbosity)
        log_file_handler.setFormatter(logging.Formatter(
            '%(asctime)s:%(levelname)s:%(message)s'))
        logger.addHandler(log_file_handler)
        return

    def build(self):
        for pkg in self.pkgs_name:
            # print(os.path.abspath(os.curdir))
            matched_pkg = acbs_find(pkg).acbs_pkg_match()
            if isinstance(matched_pkg, list):
                logging.info('Package build list found: \033[36m%s (%s)\033[0m' %
                             (os.path.basename(pkg), len(matched_pkg)))
                return self.build_pkgs(matched_pkg + self.pkgs_name)
            if matched_pkg is None:
                raise acbs_utils.ACBSGeneralError(
                    'No valid candidate package found for \033[36m%s\033[0m.' % (pkg))
                return 1
            else:
                if build_ind_pkg(matched_pkg) == 0:  # FIXME
                    continue
                else:
                    return 1
        return 0
