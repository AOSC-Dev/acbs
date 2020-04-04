import subprocess
# import ptyprocess
import os
import time
import signal
import shutil
import logging
import tempfile

from acbs import utils
from acbs import const
from acbs.loader import LoaderHelper
from acbs.utils import ACBSVariables

SIGNAMES = dict((k, v) for v, k in reversed(sorted(signal.__dict__.items()))
     if v.startswith('SIG') and not v.startswith('SIG_'))

class Autobuild(object):

    def __init__(self, tmp_dir_loc, repo_dir, pkg_info):
        self.tmp_dir_loc = tmp_dir_loc
        self.abdir = None
        logging.info('Build dir location: {}'.format(tmp_dir_loc))
        self.repo_dir = repo_dir
        self.pkg_info = pkg_info
        self.pkg_name = self.pkg_info.pkg_name
        self.pkg_data = self.pkg_info.abbs_data
        self.issubpkg = self.pkg_info.issubpkg

    def determine_subdir(self) -> str:
        os.chdir(self.tmp_dir_loc)  # Reset location
        if os.path.isdir(self.pkg_name + '-' + self.pkg_data['VER']):
            return self.pkg_name + '-' + self.pkg_data['VER']
        elif os.path.isdir(self.pkg_name):
            return self.pkg_name
        for dirs, subdirs, files in os.walk(self.tmp_dir_loc):
            if len(subdirs) == 1:
                return os.path.join(self.tmp_dir_loc, subdirs[0])
            elif not subdirs:
                return '.'
            else:
                raise ValueError(
                    'Failed to determine sub-directory, please specify manually.')

    def copy_abd(self):
        os.chdir(self.tmp_dir_loc)
        if self.pkg_data.get('DUMMYSRC') in ('true', '1', 'y'):
            self.pkg_data['SUBDIR'] = '.'
        LoaderHelper.callback('before_copy_defines')
        if self.pkg_data.get('SUBDIR'):
            try:
                os.chdir(self.pkg_data['SUBDIR'])
            except FileNotFoundError as ex:
                raise OSError(
                    'Failed to enter sub-directory `{}\'!'.format(self.pkg_data['SUBDIR'])) from ex
        else:
            try:
                os.chdir(self.pkg_name + '-' + self.pkg_data['VER'])
            except Exception:
                try:
                    os.chdir(self.determine_subdir())
                except Exception as ex:
                    raise ValueError(
                        'Failed to determine sub-directory, please specify manually.') from ex
        self.abdir = os.path.abspath(os.path.curdir)
        target_dir = os.path.abspath(os.path.join(os.path.curdir, 'autobuild'))
        if os.path.exists(target_dir):
            shutil.rmtree(target_dir)
        try:
            shutil.copytree(self.repo_dir, target_dir, symlinks=True)
            self.abdir = os.path.abspath(os.path.curdir)
        except Exception as ex:
            raise Exception(
                'Error occurred when copying files from tree!') from ex

    def timed_start_ab3(self, *args, **kwargs):
        def helper_gen_msg():
            return 'Time for building %s%s%s' % (const.ANSI_LT_CYAN,
                                                 self.pkg_name,
                                                 const.ANSI_RST)

        @utils.time_this(desc_msg=helper_gen_msg(), vars_ctx=ACBSVariables)
        def start_ab3(self, *args, **kwargs):
            def start_logged():
                with tempfile.NamedTemporaryFile(prefix='acbs-build_', suffix='.log', dir=os.path.curdir, delete=False) as f:
                    logging.info('Build log: %s' % f.name)
                    header = '!!ACBS Build Log\n!!Build start: %s\n' % time.ctime()
                    f.write(header.encode())
                    ab_proc = pexpect.spawn('autobuild', logfile=f)
                    term_size = shutil.get_terminal_size()
                    ab_proc.setwinsize(rows=term_size.lines,
                                       cols=term_size.columns)
                    ab_proc.interact()
                    while (not ab_proc.isalive()) and (not ab_proc.terminated):
                        ab_proc.terminate()
                    exit_status = ab_proc.exitstatus
                    signal_status = ab_proc.signalstatus
                    if signal_status:
                        footer = '\n!!Build killed with %s' % SIGNAMES[signal_status]
                    else:
                        footer = '\n!!Build exited with %s' % exit_status
                    f.write(footer.encode())
                    if signal_status or exit_status:
                        raise subprocess.CalledProcessError(
                            ab_proc.status, 'autobuild')

            def start_nolog():
                subprocess.check_call(['autobuild'])

            os.chdir(self.abdir)
            shadow_defines_loc = self.abdir
            LoaderHelper.callback('before_build')
            #parser_obj = Parser()
            #parser_obj.abbs_spec = self.pkg_data
            #parser_obj.defines_file_loc = shadow_defines_loc
            #parser_obj.parser_pass_through()
            self.pkg_info.write_ab3_defines(shadow_defines_loc)
            build_logging = True
            try:
                import pexpect
            except ImportError:
                logging.warning('Build log turned off due to lack dependency')
                build_logging = False
            try:
                if build_logging:
                    start_logged()
                else:
                    start_nolog()
            except subprocess.CalledProcessError as ex:
                logging.error('Autobuild 3 reported a building failure!')
                raise
            if self.issubpkg:
                shutil.rmtree(os.path.abspath(os.path.curdir) + '/autobuild/')
        return start_ab3(self)
