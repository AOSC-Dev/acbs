import subprocess
# import ptyprocess
import pty
import time
import os
import shutil

from lib.acbs_utils import acbs_utils
from lib.acbs_parser import acbs_parser


class acbs_start_ab(object):
    def __init__(self, tmp_dir_loc, repo_dir, pkg_info, rm_abdir=False):
        self.tmp_dir_loc = tmp_dir_loc
        self.repo_dir = repo_dir
        self.pkg_info = pkg_info
        self.rm_abdir = rm_abdir
        global pkg_name
        pkg_name = pkg_info['NAME']

    def copy_abd(self):
        if self.pkg_info['SUBDIR'] != '':
            try:
                os.chdir(self.pkg_info['SUBDIR'])
            except:
                acbs_utils.err_msg('Failed to enter sub-directory!')
                return False
        else:
            try:
                os.chdir(self.pkg_info['NAME'] + '-' + self.pkg_info['VER'])
            except:
                try:
                    os.chdir(self.pkg_info['NAME'])
                except:
                    acbs_utils.err_msg(
                        'Failed to determine sub-directory, please specify manually.')
                    return False
        try:
            shutil.copytree(self.repo_dir,
                            os.path.abspath(os.path.curdir) + '/autobuild/', symlinks=True)
        except:
            acbs_utils.err_msg('Error occurred when copying files from tree!')
            return False
        return True

    @acbs_utils.time_this(desc_msg='Time for building {}'.format(pkg_name))
    def start_ab3(self):
        os.chdir(self.tmp_dir_loc)
        if not self.copy_abd(self.tmp_dir_loc, self.repo_dir, self.pkg_info):
            return False
        # For logging support: ptyprocess.PtyProcessUnicode.spawn(['autobuild'])
        shadow_defines_loc = os.path.abspath(os.path.curdir)
        if not acbs_parser.parser_pass_through(self.pkg_info, shadow_defines_loc):
            return False
        try:
            subprocess.check_call(['autobuild'])
        except:
            return False
        if self.rm_abdir is True:
            shutil.rmtree(os.path.abspath(os.path.curdir) + '/autobuild/')
        # Will get better display later
        return True
