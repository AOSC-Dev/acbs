import subprocess
import os
from urllib import parse
import logging

from lib.acbs_src_process import src_proc_dispatcher
from lib.acbs_utils import acbs_utils


class acbs_src_fetch(object):

    def __init__(self, pkg_info, dump_loc='/var/cache/acbs/tarballs/'):
        self.pkg_info = pkg_info
        self.dump_loc = dump_loc

    def src_dispatcher(self):
        if self.pkg_info['DUMMYSRC'] != '':
            logging.info('Not fetching dummy source as required.')
            return src_proc_dispatcher(self.pkg_info['NAME'], None, self.dump_loc)
        if self.pkg_info['SRCTBL'] != '':
            return self.src_url_dispatcher()
        for src in ['SRCTBL', 'GITSRC', 'SVNSRC', 'HGSRC', 'BZRSRC']:
            if len(self.pkg_info[src]) > 0:
                exec('ret=self.src_%s_fetch()' % (src.strip('SRC').lower()))
                ret_code = locals()['ret']
                return ret_code
        return False

    def src_url_dispatcher(self):
        pkg_info = self.pkg_info
        url = pkg_info['SRCTBL']
        # url_array = url.split('\n').split(' ') #for future usage
        pkg_name = pkg_info['NAME']
        pkg_ver = pkg_info['VER']
        try:
            proto, _, _, _, _, _ = parse.urlparse(url)
            # Some of the varibles maybe used in the future, now leave them
            # as placeholder
        except:
            logging.exception('Illegal source URL!!!')
            return False
        if proto in ['http', 'https', 'ftp', 'ftps', 'ftpes']:
            src_tbl_name = pkg_name + '-' + pkg_ver
            src_name = os.path.basename(url)
            if self.src_tbl_fetch(url, src_tbl_name):
                return src_proc_dispatcher(pkg_name, src_name, self.dump_loc)
        elif proto in ['git', 'hg', 'svn', 'bzr', 'bk']:  # or proto == 'git+https'
            logging.warning(
                'In spec file: This source seems to refers to a VCS repository, but you misplaced it.')
            if exec('self.src_%s_fetch()' % (proto)):
                return src_proc_dispatcher(pkg_name, pkg_name, self.dump_loc)
        else:
            logging.error('Unknown protocol {}'.format(proto))
            return False
        return False

    def src_git_fetch(self):
        pkg_info = self.pkg_info
        if not acbs_utils.test_progs(['git', '--version']):
            logging.error('Git is not installed!')
            return False
        if pkg_info['GITSRC'] == '':
            logging.error('Source URL is empty!')
            return False
        if pkg_info['GITCO'] == '':
            logging.warning(
                'Source revision not specified! Will use HEAD commit instead!')
        logging.info('Cloning Git repository...')
        os.chdir(self.dump_loc)
        try:
            if os.path.isdir(pkg_info['NAME']) and os.path.isdir(pkg_info['NAME'] + '/.git'):
                os.chdir(pkg_info['NAME'])
                logging.info('Updating existing repository...')
                subprocess.check_call(['git', 'pull', '-f'])
            else:
                subprocess.check_call(
                    ['git', 'clone', pkg_info['GITSRC'], pkg_info['NAME']])
                os.chdir(pkg_info['NAME'])
            if pkg_info['GITBRCH'] != '':
                subprocess.check_call(
                    ['git', 'checkout', '-f', pkg_info['GITBRCH']])
            if pkg_info['GITCO'] != '':
                subprocess.check_call(
                    ['git', 'checkout', '-f', pkg_info['GITCO']])
        except:
            logging.critical('Failed to fetch source!')
            return False
        return src_proc_dispatcher(pkg_info['NAME'], pkg_info['NAME'], self.dump_loc)

    def src_tbl_fetch(self, url, pkg_slug):
        use_progs = self.test_downloaders()
        src_name = os.path.basename(url)
        full_path = os.path.join(self.dump_loc, src_name)
        flag_file = full_path + '.dl'
        if os.path.exists(full_path) and (not os.path.exists(flag_file)):
            return True
        with open(flag_file, 'wt') as flag:
            flag.write('acbs flag: DO NOT DELETE!')
        for i in use_progs:
            try:
                # print('self.%s_get(%r, output=%r)' % (i, url, full_path))
                exec('self.%s_get(url=%r, output=%r)' % (i, url, full_path))
                os.unlink(flag_file)
                break
            except KeyboardInterrupt:
                acbs_utils.err_msg('You aborted the download!')
                return False
            except NameError:
                logging.exception('An Internal Error occurred!')
                raise NameError()
            except AssertionError:
                continue
            except:
                logging.exception('Something happend!')
                return False
        return True

    def src_svn_fetch(self):
        if not acbs_utils.test_progs(['svn', '-h']):
            logging.error('Subverion is not installed!')
            return False
        if self.pkg_info['SVNSRC'] == '':
            logging.error('Source URL is empty!')
            return False
        if self.pkg_info['SVNCO'] == '':
            logging.warning(
                'Source revision not specified! Will use latest revision instead!')
            self.pkg_info['SVNCO'] = 'HEAD'
        subprocess.check_call(['svn', 'co', '-r', self.pkg_info['SVNCO']])
        return True

    def src_hg_fetch(self):
        raise NotImplementedError()
        return True

    def src_bzr_fetch(self):
        raise NotImplementedError()
        return True

    def src_bk_fetch(self):
        raise NotImplementedError()
        return True

    '''
    External downloaders
    '''

    def test_downloaders(self):
        use_progs = []
        if acbs_utils.test_progs(['aria2c', '-h']):
            use_progs.append('aria')
        if acbs_utils.test_progs(['wget', '-h']):
            use_progs.append('wget')
        if acbs_utils.test_progs(['curl', '-h']):
            use_progs.append('curl')
        if acbs_utils.test_progs(['axel', '-h']):
            use_progs.append('axel')
        return use_progs

    def axel_get(self, url, threads=4, output=None):
        axel_cmd = ['axel', '-n', threads, '-a', url]
        if output is not None:
            axel_cmd.insert(4, '-o')
            axel_cmd.insert(5, output)
        try:
            subprocess.check_call(axel_cmd)
        except KeyboardInterrupt:
            raise KeyboardInterrupt()
        except:
            raise AssertionError('Failed to fetch source with Axel!')
        return

    def curl_get(self, url, output=None):
        curl_cmd = ['curl', url]  # , '-k'
        if output is not None:
            curl_cmd.insert(2, '-o')
            curl_cmd.insert(3, output)
        else:
            curl_cmd.insert(2, '-O')
        try:
            subprocess.check_call(curl_cmd)
        except KeyboardInterrupt:
            raise KeyboardInterrupt()
        except:
            raise AssertionError('Failed to fetch source with cURL!')
        return

    def wget_get(self, url, output):
        wget_cmd = ['wget', '-c', url]  # ,'--no-check-certificate'
        if output is not None:
            wget_cmd.insert(2, '-O')
            wget_cmd.insert(3, output)
        try:
            subprocess.check_call(wget_cmd)
        except KeyboardInterrupt:
            raise KeyboardInterrupt()
        except:
            raise AssertionError('Failed to fetch source with Wget!')
        return

    def aria_get(self, url, threads=3, output=None):
        if os.path.exists(output) and not os.path.exists(output + '.aria2'):
            return
        aria_cmd = ['aria2c', '--max-connection-per-server={}'.format(
            threads), url, '--auto-file-renaming=false']
        # ,'--check-certificate=false'
        if output is not None:
            aria_cmd.insert(2, '-d')
            aria_cmd.insert(3, '/'.join(output.split('/')[:-1]))  # Temporary
            aria_cmd.insert(4, '-o')
            aria_cmd.insert(5, output.split('/')[-1])
        try:
            subprocess.check_call(aria_cmd)
        except KeyboardInterrupt:
            raise KeyboardInterrupt()
        except:
            raise AssertionError('Failed to fetch source with Aria2!')
        return
