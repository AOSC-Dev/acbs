import subprocess
# import ptyprocess
import os
import shutil
import logging

from lib.acbs_utils import acbs_utils
from lib.acbs_parser import acbs_parser
from lib.acbs_const import acbs_const


class acbs_start_ab(object):
    def __init__(self, tmp_dir_loc, repo_dir, pkg_info, rm_abdir=False):
        self.tmp_dir_loc = tmp_dir_loc
        self.abdir = None
        logging.info('Build dir location: {}'.format(tmp_dir_loc))
        self.repo_dir = repo_dir
        self.pkg_data = pkg_info
        self.rm_abdir = rm_abdir
        global pkg_name
        self.pkg_name = self.pkg_data.name
        self.pkg_info = self.pkg_data.buffer['abbs_data']

    def copy_abd(self):
        os.chdir(self.tmp_dir_loc)
        if self.pkg_info['DUMMYSRC'] in ['true', '1']:
            self.pkg_info['SUBDIR'] = '.'
        if self.pkg_info['SUBDIR'] != '':
            try:
                os.chdir(self.pkg_info['SUBDIR'])
            except FileNotFoundError as ex:
                raise OSError('Failed to enter sub-directory `{}\'!'.format(self.pkg_info['SUBDIR'])) from ex
        else:
            try:
                os.chdir(self.pkg_info['NAME'] + '-' + self.pkg_info['VER'])
            except:
                try:
                    os.chdir(self.pkg_info['NAME'])
                except Exception as ex:
                    raise ValueError(
                        'Failed to determine sub-directory, please specify manually.') from ex
        self.abdir = os.path.abspath(os.path.curdir)
        try:
            shutil.copytree(self.repo_dir,
                            os.path.abspath(os.path.curdir) + '/autobuild/', symlinks=True)
            self.abdir = os.path.abspath(os.path.curdir)
        except Exception as ex:
            raise Exception('Error occurred when copying files from tree!') from ex
        return

    def timed_start_ab3(self):
        def helper_gen_msg():
            acc = acbs_const()
            return 'Time for building {}{}{}'.format(acc.ANSI_LT_CYAN, self.pkg_info['NAME'], acc.ANSI_RST)

        @acbs_utils.time_this(desc_msg=helper_gen_msg())
        def start_ab3(self):
            os.chdir(self.abdir)
            # For logging support: ptyprocess.PtyProcessUnicode.spawn(['autobuild'])
            shadow_defines_loc = self.abdir
            parser_obj = acbs_parser()
            parser_obj.abbs_spec = self.pkg_info
            parser_obj.defines_file_loc = shadow_defines_loc
            parser_obj.parser_pass_through()
            try:
                subprocess.check_call(['autobuild'])
            except subprocess.CalledProcessError as ex:
                raise Exception('Autobuild 3 reported a building failure!') from ex
            if self.rm_abdir:
                shutil.rmtree(os.path.abspath(os.path.curdir) + '/autobuild/')
            return
        return start_ab3(self)
