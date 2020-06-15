from typing import List, Optional, Dict, Tuple, Deque
from acbs.base import ACBSPackageInfo
import logging


installed_cache: List[str] = []
available_cache: List[str] = []


def filter_dependencies(package: ACBSPackageInfo) -> ACBSPackageInfo:
    installables = []
    deps = []
    for dep in package.deps:
        if check_if_installed(dep):
            continue
        if check_if_available(dep):
            installables.append(dep)
            continue
        deps.append(dep)
    package.deps = deps
    package.installables = installables
    return package


def check_if_installed(name: str) -> bool:
    logging.debug('Checking if %s is installed' % name)
    return True


def check_if_available(name: str) -> bool:
    logging.debug('Checking if %s is available' % name)
    return True


def install_from_repo(packages: List[str]):
    logging.debug('Installing %s' % packages)
    return
