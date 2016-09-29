import os
import logging

from ..acbs_utils import acbs_utils


class acbs_vcs(object):

    def __init__(self):
        vcs_mod_dir = os.path.dirname(os.path.realpath(__file__))
        mod_files = os.listdir(vcs_mod_dir)
        self.backends = []
        for i in mod_files:
            if i.endswith('.sh'):
                self.backends.append(os.path.join(vcs_mod_dir, i))
        logging.debug('Found backends: {}'.format(self.backends))
        return

    def vcs_repo_url(self, repo_dir):
        """
        Get default URL of the given repository

        :param repo_dir: The full path to repository directory
        :return: The default pull URL of the repository
        :raises ValueError: The parameter `repo_dir` cannot be None
        """
        if repo_dir is None:
            raise ValueError('`repo_dir` can\'t be None!')
        repo_url = self.vcs_executor('repourl', repo_dir, need_ret=True)
        if not repo_url:
            return None
        return

    def vcs_executor(self, action, param=None, url_proto=None, need_ret=False):
        """
        Execute commands of various VCS systems

        :param action: Actually functions in scripts
        :param param: Parameters to be passed
        :param url_proto: `URL or protocol`
        """
        if (url_proto is not None) and (url_proto.index('://') > 2):
            proto = url_proto.split('://')[0]
        else:
            acbs_utils().err_msg('Invaild URL: %r' % url_proto)
        if proto not in self.backends:
            raise NotImplementedError('Unsupported VCS system: %s' % proto)
            return False

    def vcs_fetch_src(self, url, repo_dir, proto=None):
        if proto is None:
            proto = url.split('://')[0]
        if proto not in self.backends:
            acbs_utils.acbs_utils().err_msg('Unsupported VCS system: %s' % proto)
            return False
