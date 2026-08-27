import logging
import re
import shutil
import subprocess

logger = logging.getLogger(__name__)

from acbs.base import ACBSPackageInfo
from acbs.utils import get_arch_name

installed_cache: dict[str, bool] = {}
available_cache: dict[str, bool] = {}
use_native_bindings: bool = True
reorder_mode: bool = False

try:
    from acbs.miniapt_query import apt_init_system
    from acbs.miniapt_query import check_if_available as apt_check_if_available
    if not apt_init_system():
        raise ImportError('Initialization failure.')
except ImportError:
    use_native_bindings = False
    apt_init_system = None
    apt_check_if_available = None


def enable_reorder_mode(enable: bool | None=None) -> bool:
    global reorder_mode
    if enable is not None:
        reorder_mode = enable
    return reorder_mode


def filter_dependencies(package: ACBSPackageInfo) -> ACBSPackageInfo:
    installables = []
    deps = []
    for dep in package.deps:
        if check_if_installed(dep):
            if reorder_mode:
                # HACK: when reordering dependencies, we need to pretend that they needs to be installed
                installables.append(dep)
            continue
        if check_if_available(dep):
            installables.append(dep)
            continue
        deps.append(dep)
    package.deps = deps
    package.installables = installables
    return package


def escape_package_name(name: str) -> str:
    return re.sub(r'([+*?])', '\\\\\\1', name)


def escape_package_name_install(name: str) -> str:
    escaped = escape_package_name(name)
    if escaped.endswith(('+', '-')):
        return f'{escaped}+'
    return escaped


def fix_pm_states(escaped: list[str]):
    count = 0
    while count < 3:
        try:
            subprocess.call(['dpkg', '--configure', '-a'])
            subprocess.check_call(['apt-get', 'install', '-yf'])
            if escaped:
                command = ['apt-get', 'install', '-y']
                command.extend(escaped)
                subprocess.check_call(command, env={'DEBIAN_FRONTEND': 'noninteractive'})
            return
        except subprocess.CalledProcessError:
            count += 1
            continue
    raise RuntimeError('Unable to correct package manager states...')


def check_if_installed(name: str) -> bool:
    logger.debug('Checking if %s is installed', name)
    cached = installed_cache.get(name)
    if cached is not None:
        return cached
    if use_native_bindings:
        assert callable(apt_check_if_available)
        logger.debug('... using libapt-pkg')
        result = apt_check_if_available(name)
        if result == 0:
            installed_cache[name] = True
            return True
        elif result == 1:
            installed_cache[name] = False
            available_cache[name] = True
            return False
        elif result == 2:
            installed_cache[name] = False
            available_cache[name] = False
            return False
        elif result == -4:
            fix_pm_states([])
            return check_if_installed(name)
        else:
            raise RuntimeError(f'libapt-pkg binding returned error: {result}')
    try:
        subprocess.check_output(['dpkg', '-s', name], stderr=subprocess.STDOUT)
        installed_cache[name] = True
        return True
    except subprocess.CalledProcessError:
        installed_cache[name] = False
        return False


def check_if_available(name: str) -> bool:
    logger.debug('Checking if %s is available', name)
    cached = available_cache.get(name)
    if cached is not None:
        return cached
    if use_native_bindings:
        assert callable(apt_check_if_available)
        logger.debug('... using libapt-pkg')
        if apt_check_if_available(name) != 1:
            return False
    try:
        subprocess.check_output(
            ['apt-cache', 'show', escape_package_name(name)], stderr=subprocess.STDOUT)
        logger.debug('Checking if %s can be installed', name)
        subprocess.check_output(
            ['apt-get', 'install', '-s', name], stderr=subprocess.STDOUT, env={'DEBIAN_FRONTEND': 'noninteractive'})
        available_cache[name] = True
        return True
    except subprocess.CalledProcessError:
        available_cache[name] = False
        return False


def install_from_repo(packages: list[str], force_use_apt=False):
    # FIXME: RISC-V build hosts is unreliable when using oma: random lock-ups
    # during `oma refresh'. Disabling oma to workaround potential lock-ups.
    oma_exists = False
    if shutil.which('oma') is not None:
        oma_exists = True
    if get_arch_name() == "riscv64" or force_use_apt or not oma_exists:
        return install_from_repo_apt(packages)

    return install_from_repo_oma(packages) or install_from_repo_apt(packages)


def install_from_repo_apt(packages: list[str]):
    logger.debug('Installing %s', packages)
    escaped = []
    for package in packages:
        escaped.append(escape_package_name_install(package))
    command = ['apt-get', 'install', '-y', '-o', 'Dpkg::Options::=--force-confnew']
    command.extend(escaped)
    try:
        subprocess.check_call(command, env={'DEBIAN_FRONTEND': 'noninteractive'})
    except subprocess.CalledProcessError:
        logger.warning(
            'Failed to install dependencies, attempting to correct issues...')
        fix_pm_states(escaped)


def install_from_repo_oma(packages: list[str]) -> bool:
    logger.debug('Installing %s from oma', packages)
    command = ['oma', 'install', '-y', '--force-confnew', '--no-progress', '--force-unsafe-io', '--no-bell', '--no-clean']
    command.extend(packages)
    try:
        subprocess.check_call(command)
    except subprocess.CalledProcessError:
        logger.warning(
            'Failed to use oma install dependencies, fallbacking to apt...')
        return False
    return True
