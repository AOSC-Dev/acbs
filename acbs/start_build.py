import subprocess
# import ptyprocess
import os
import shutil
import logging

from acbs import utils
from acbs import const
from acbs.parser import Parser


class Autobuild(object):
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

    def determine_subdir(self):
        if os.path.isdir(self.pkg_info['NAME'] + '-' + self.pkg_info['VER']):
            return self.pkg_info['NAME'] + '-' + self.pkg_info['VER']
        elif os.path.isdir(self.pkg_info['NAME']):
            return self.pkg_info['NAME']
        for dirs, subdirs, files in os.walk(self.tmp_dir_loc):
            if len(subdirs) == 1:
                return os.path.join(self.tmp_dir_loc, subdirs[0])
            elif len(subdirs) == 0:
                return '.'
            else:
                raise ValueError(
                    'Failed to determine sub-directory, please specify manually.')
                return

    def copy_abd(self):
        os.chdir(self.tmp_dir_loc)
        if self.pkg_info['DUMMYSRC'] in ['true', '1', 'y']:
            self.pkg_info['SUBDIR'] = '.'
        self.determine_subdir()
        if self.pkg_info['SUBDIR']:
            try:
                os.chdir(self.pkg_info['SUBDIR'])
            except FileNotFoundError as ex:
                raise OSError('Failed to enter sub-directory `{}\'!'.format(self.pkg_info['SUBDIR'])) from ex
        else:
            try:
                os.chdir(self.pkg_info['NAME'] + '-' + self.pkg_info['VER'])
            except:
                try:
                    os.chdir(self.determine_subdir())
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

    def timed_start_ab3(self, *args, **kwargs):
        def helper_gen_msg():
            return 'Time for building {}{}{}'.format(const.ANSI_LT_CYAN, self.pkg_info['NAME'], const.ANSI_RST)

        @utils.time_this(desc_msg=helper_gen_msg())
        def start_ab3(self, *args, **kwargs):
            os.chdir(self.abdir)
            # For logging support: ptyprocess.PtyProcessUnicode.spawn(['autobuild'])
            shadow_defines_loc = self.abdir
            parser_obj = Parser()
            parser_obj.abbs_spec = self.pkg_info
            parser_obj.defines_file_loc = shadow_defines_loc
            parser_obj.parser_pass_through()
            try:
                subprocess.check_call(['autobuild'])
            except subprocess.CalledProcessError as ex:
                raise Exception('Autobuild 3 reported a building failure!') from ex
            if self.rm_abdir:
                shutil.rmtree(os.path.abspath(os.path.curdir) + '/autobuild/')
        return start_ab3(self)
