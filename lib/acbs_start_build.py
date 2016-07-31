import subprocess
# import ptyprocess
import pty
import time
import os
import shutil

from lib.acbs_utils import err_msg
from lib.acbs_parser import *


def copy_abd(tmp_dir_loc, repo_dir, pkg_info):
    if pkg_info['SUBDIR'] != '':
        try:
            os.chdir(pkg_info['SUBDIR'])
        except:
            err_msg('Failed to enter sub-directory!')
            return False
    else:
        try:
            os.chdir(pkg_info['NAME'] + '-' + pkg_info['VER'])
        except:
            try:
                os.chdir(pkg_info['NAME'])
            except:
                err_msg(
                    'Failed to determine sub-directory, please specify manually.')
                return False
    try:
        shutil.copytree(repo_dir,
                        os.path.abspath(os.path.curdir) + '/autobuild/', symlinks=True)
    except:
        err_msg('Error occurred when copying files from tree!')
        return False
    return True


def start_ab3(tmp_dir_loc, repo_dir, pkg_info, rm_abdir=False):
    start_time = int(time.time())
    os.chdir(tmp_dir_loc)
    if not copy_abd(tmp_dir_loc, repo_dir, pkg_info):
        return False
    # For logging support: ptyprocess.PtyProcessUnicode.spawn(['autobuild'])
    shadow_defines_loc = os.path.abspath(os.path.curdir)
    if not parser_pass_through(pkg_info, shadow_defines_loc):
        return False
    try:
        subprocess.check_call(['autobuild'])
    except:
        return False
    time_span = int(time.time()) - start_time
    print('>>>>>>>>>>>>>>>>>> Time for building\033[36m {} \033[0m:\033[36m {} \033[0mseconds'.format(
        pkg_info['NAME'], time_span))
    if rm_abdir is True:
        shutil.rmtree(os.path.abspath(os.path.curdir) + '/autobuild/')
    # Will get better display later
    return True
