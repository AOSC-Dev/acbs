import os
import logging

from .. import utils


class VCS(object):

    def __init__(self, url, repo_dir, proto=None):
        self.vcs_mod_dir = os.path.dirname(os.path.realpath(__file__))
        self.vcs_mod_files = os.listdir(self.vcs_mod_dir)
        self.vcs_backends = []
        self.backend_files = []
        self.proto = proto
        self.target_url = url
        self.repo_dir = repo_dir
        for i in self.vcs_mod_files:
            if i.endswith('.sh'):
                self.vcs_backends.append(os.path.basename(i).split('.sh')[0])
                self.backend_files.append(os.path.join(self.vcs_mod_dir, i))
        logging.debug('Found vcs_backends: {}'.format(self.vcs_backends))
        return

    def vcs_repo_update(self):
        return self.vcs_executor(action='vcs_repoupdate', url=self.target_url, param=self.target_url)

    def vcs_chk_proto(self, url, proto=None):
        if self.proto:
            proto = self.proto
        import re
        if re.match(pattern=r'(\w+)\://', string=url):
            proto = re.search(pattern=r'(\w+)\://', string=url).group(1)
        elif re.match(pattern=r'lp:(.*?)', string=url):
            proto = 'bzr'
        elif re.match(pattern=r'(\w+)::', string=url):
            proto = re.search(pattern=r'(\w+)::(.*)', string=url).group(1)
        else:
            raise ValueError('Invaild URL: %r' % url)
        if proto.lower() not in self.vcs_backends:
            raise NotImplementedError('Unsupported VCS system: %s' % proto)
        return proto

    def vcs_repo_url(self):
        """
        Get default URL of the given repository

        :param repo_dir: The full path to repository directory
        :return: The default pull URL of the repository
        :raises ValueError: The parameter `repo_dir` cannot be None
        """
        if self.repo_dir is None:
            raise ValueError('`repo_dir` can\'t be None!')
        repo_url = self.vcs_executor(
            'vcs_repourl', param=self.repo_dir, proto=self.proto, need_ret=True)
        if (not repo_url) or (self.repo_dir == '?'):
            return
        return repo_url.strip()

    def vcs_executor(self, action, url=None, param=None, proto=None, need_ret=False):
        """
        Execute commands of various VCS systems

        :param action: Actually functions in scripts
        :param param: Parameters to be passed
        :param url_proto: `URL or protocol`
        """
        proto = proto or self.proto
        if not proto:
            proto = self.vcs_chk_proto(url)
            if not proto:
                raise ValueError('VCS protocol unspecified')
        logging.debug('VCS: %s: %s(%s)' % (proto, action, param))
        sh_ret = utils.sh_executor(
            os.path.join(self.vcs_mod_dir, '{}.sh'.format(proto)), action, param, not need_ret)
        if (not sh_ret):
            raise Exception('Error occurred when executing VCS commands')
        return sh_ret

    def vcs_fetch_src(self, proto=None):
        logging.debug('Received VCS module name: {}'.format(proto or self.proto))
        logging.debug('Fetching {}'.format(self.target_url))
        if not (proto or self.proto):
            proto = self.vcs_chk_proto(self.target_url)
            if not proto:
                raise ValueError('Unknow VCS protocol!')
        try:
            os.listdir(self.repo_dir)
        except FileNotFoundError:
            self.vcs_executor('vcs_repofetch', param=' '.join([self.target_url, self.repo_dir]), url=self.target_url, proto=proto)
            return
        repo_url = self.vcs_repo_url()
        if repo_url not in ['?', None, ''] and repo_url != self.target_url:
            logging.debug(
                'Current VCS URL: {}, requested URL: {}'.format(repo_url, self.target_url))
            logging.error('Target URL and existing VCS URL mismatch!')
            logging.error('Target: %s VS Existing %s' % (repo_url, self.target_url))
            logging.warning('You have the following choices:')
            logging.warning('\t1. Remove the existing directory')
            logging.warning('\t2. Correct the URL in either `spec` file or stash')
            raise Exception('See above...')
            '''
            import shutil
            shutil.rmtree(self.repo_dir)
            '''
        else:
            os.chdir(self.repo_dir)
            return self.vcs_repo_update()
        return self.vcs_executor('vcs_repofetch', param=' '.join([self.target_url, self.repo_dir]), url=self.target_url, proto=proto)
