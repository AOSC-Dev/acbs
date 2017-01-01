from .pm import acbs_pm
from acbs.utils import ACBSGeneralError
import logging


class acbs_deps(object):

    def __init__(self):
        self.acbs_pm = acbs_pm()
        return

    def search_deps(self, search_pkgs):
        pkgs_miss = self.acbs_pm.query_current_miss_pkgs(search_pkgs)
        pkgs_to_install = self.acbs_pm.query_online_pkgs(pkgs_miss)
        pkgs_not_avail = (set(pkgs_miss) - set(pkgs_to_install))
        if len(pkgs_not_avail) > 0:
            return None, pkgs_not_avail
        return pkgs_to_install, None

    def process_deps(self, build_deps, run_deps, pkg_slug):
        logging.info('Checking for dependencies, this may take a while...')
        search_pkgs_tmp = (build_deps + run_deps)
        search_pkgs = []
        logging.debug('Searching dependencies: {}'.format(search_pkgs_tmp))
        for i in search_pkgs_tmp:
            if i == pkg_slug:
                _, pkgs_not_avail = self.search_deps(i)
                if pkgs_not_avail:
                    raise ACBSGeneralError(
                        'The package can\'t depends on its self!')
                else:
                    logging.warning(
                        'The package depends on its self, however, it has been built at least once.')
            if not i.strip():
                continue
            search_pkgs.append(i)
        pkgs_to_install, pkgs_not_avail = self.search_deps(search_pkgs)
        if not pkgs_not_avail:
            pkgs_not_avail = []
        if len(pkgs_not_avail):
            logging.info(
                'Building in-tree dependencies: \033[36m{}\033[0m'.format(' '.join(pkgs_not_avail)))
            return pkgs_not_avail
        if (not pkgs_to_install) or (not len(pkgs_to_install)):
            logging.info('All dependencies are met. Continue.')
            return
        logging.info('Will install \033[36m{}\033[0m as required.'.format(
            ' '.join(pkgs_to_install)))
        try:
            self.acbs_pm.install_pkgs(pkgs_to_install)
        except Exception as ex:
            raise ACBSGeneralError(
                'Something went wrong when processing dependencies...') from ex
        return
