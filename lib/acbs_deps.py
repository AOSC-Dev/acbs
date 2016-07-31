from .pm.acbs_dpkg import *
from lib.acbs_utils import *


def search_deps(search_pkgs):
    pkgs_miss = dpkg_search_pkgs(search_pkgs)
    pkgs_to_install = apt_query_pkgs(pkgs_miss)
    pkgs_not_avail = (set(pkgs_miss) - set(pkgs_to_install))
    if len(pkgs_not_avail) > 0:
        return None, pkgs_not_avail
    return pkgs_to_install, None


def process_deps(build_deps, run_deps, pkg_slug):
    print('[I] Checking for dependencies, this may take a while...')
    search_pkgs_tmp = (build_deps + ' ' + run_deps).split(' ')
    search_pkgs = []
    for i in search_pkgs_tmp:
        if i == pkg_slug:
            err_msg('The package can\'t depends on its self!')
            return False, None
        if i == '' or i == ' ':
            continue
        search_pkgs.append(i)

    pkgs_to_install, pkgs_not_avail = search_deps(search_pkgs)
    if pkgs_not_avail is None:
        pkgs_not_avail = []
    if len(pkgs_not_avail) > 0:
        print('[I] Building in-tree dependencies: \033[36m{}\033[0m'.format(arr2str(pkgs_not_avail)))
        return False, pkgs_not_avail
    if (pkgs_to_install is None) or len(pkgs_to_install) == 0:
        print('[I] All dependencies are met.')
        return True, None
    print('[I] Will install \033[36m{}\033[0m as required.'.format(arr2str(pkgs_to_install)))
    if not dpkg_req_dep_inst(pkgs_to_install):
        return False, None
    return True, None
