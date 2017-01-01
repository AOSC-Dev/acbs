import subprocess
import os
from urllib import parse
import logging

from acbs.src_process import SourceProcessor
from acbs import utils
from acbs.vcs import VCS


class SourceFetcher(object):

    def __init__(self, pkg_info, dump_loc='/var/cache/acbs/tarballs/'):
        self.pkg_info = pkg_info
        self.dump_loc = dump_loc
        self.pkg_name = pkg_info['NAME']
        self.src_name = None
        self.ind_dump_loc = os.path.join(self.dump_loc, self.pkg_name)

    def fetch_src(self):
        if self.pkg_info['DUMMYSRC']:
            logging.info('Not fetching dummy source as required.')
            return
        if self.pkg_info['SRCTBL']:
            return self.src_url_dispatcher()
        for src in ['SRCTBL', 'GITSRC', 'SVNSRC', 'HGSRC', 'BZRSRC']:
            if len(self.pkg_info[src]) > 0:
                if src == 'SRCTBL':
                    return self.src_tbl_fetch()
                if src in ['GITSRC', 'SVNSRC', 'HGSRC', 'BZRSRC']:
                    self.vcs_dispatcher(self.pkg_info[src], src_type=src[:-3].lower())
                    return self.pkg_name
        raise Exception('No source URL specified?!')

    def src_url_dispatcher(self):
        url = self.pkg_info['SRCTBL']
        # url_array = url.split('\n').split(' ') #for future usage
        pkg_name = self.pkg_name
        pkg_ver = self.pkg_info['VER']
        try:
            proto, _, _, _, _, _ = parse.urlparse(url)
            # Some of the varibles maybe used in the future, now leave them
            # as placeholder
        except Exception as ex:
            raise ValueError('Illegal source URL!!!') from ex
        if proto in ['http', 'https', 'ftp', 'ftps', 'ftpes']:
            src_tbl_name = pkg_name + '-' + pkg_ver
            self.src_name = os.path.basename(url)
            self.src_tbl_fetch(url, src_tbl_name)
            return self.src_name
        else:  # or proto == 'git+https'
            logging.warning(
                'In spec file: This source seems to refers to a VCS repository, but you misplaced it.')
            self.vcs_dispatcher(url)
            return pkg_name

    def src_tbl_fetch(self, url, pkg_slug):
        use_progs = self.test_downloaders()
        src_name = os.path.basename(url)
        full_path = os.path.join(self.dump_loc, src_name)
        flag_file = full_path + '.dl'
        if os.path.exists(full_path) and (not os.path.exists(flag_file)):
            return
        with open(flag_file, 'wt') as flag:
            flag.write('acbs flag: DO NOT DELETE!')
        for i in use_progs:
            try:
                getattr(self, i + '_get')(url=url, output=full_path)
                os.unlink(flag_file)
                break
            except KeyboardInterrupt as ex:
                raise KeyboardInterrupt('You aborted the download!') from ex
            except NameError:
                raise NameError('An Internal Error occurred!')
            except AssertionError:
                continue
            except Exception as ex:
                raise Exception('Something happend!') from ex
        return

    def vcs_dispatcher(self, url, src_type=None):
        logging.debug('Sending to VCS module:{} URL:{}'.format(src_type, url))
        VCS(url=url, repo_dir=os.path.join(self.dump_loc, self.pkg_name), proto=src_type).vcs_fetch_src()
        return

    '''
    External downloaders
    '''

    def test_downloaders(self):
        use_progs = []
        if utils.test_progs(['aria2c', '-h']):
            use_progs.append('aria')
        if utils.test_progs(['wget', '-h']):
            use_progs.append('wget')
        if utils.test_progs(['curl', '-h']):
            use_progs.append('curl')
        if utils.test_progs(['axel', '-h']):
            use_progs.append('axel')
        return use_progs

    def axel_get(self, url, threads=4, output=None):
        axel_cmd = ['axel', '-n', threads, '-a', url]
        if output:
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
        if output:
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
        if output:
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
        if output:
            aria_cmd.insert(2, '-d')
            aria_cmd.insert(3, '/'.join(output.split('/')[:-1]))  # Temporary
            aria_cmd.insert(4, '-o')
            aria_cmd.insert(5, os.path.basename(output))
        try:
            subprocess.check_call(aria_cmd)
        except KeyboardInterrupt:
            raise KeyboardInterrupt()
        except:
            raise AssertionError('Failed to fetch source with Aria2!')
        return
