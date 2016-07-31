import subprocess
# import os
# import sys

from ..acbs_utils import acbs_utils


def dpkg_miss_pkgs(search_pkgs):
    miss_pkgs = []
    fnd_pkgs = []
    for i in search_pkgs:
        if dpkg_query_pkgs(i):
            fnd_pkgs.append(i)
    miss_pkgs = (set(search_pkgs) - set(fnd_pkgs))
    return miss_pkgs


def dpkg_online_pkgs(pkgs):
    ext_pkgs = []
    for pkg in pkgs:
        if acbs_utils.test_progs(['apt-cache', 'show', pkg]):
            ext_pkgs.append(pkg)
    return ext_pkgs


def dpkg_inst_pkgs(pkgs):
    try:
        apt_cmd = ['apt', 'install', '-y']
        for i in pkgs:
            apt_cmd.append(i)
        subprocess.check_call(apt_cmd)
    except:
        return False
    return True


def dpkg_query_pkgs(pkg):
    return acbs_utils.test_progs(['dpkg-query', '-s', pkg])
