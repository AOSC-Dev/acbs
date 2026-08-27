import datetime
import json
import logging
import os
import re
import shutil
import signal
import subprocess
import tempfile
import time
from collections.abc import Sequence
from pathlib import Path
from typing import cast

from acbs import __version__
from acbs.ab4cfg import get_arch_override
from acbs.base import ACBSPackageInfo, ACBSSourceInfo
from acbs.bashvar import ParseException
from acbs.const import (
    ANSI_BROWN,
    ANSI_GREEN,
    ANSI_LT_CYAN,
    ANSI_RED,
    ANSI_RST,
    ANSI_YELLOW,
    AUTOBUILD_CONF_DIR,
    AUTOBUILD_DIR,
)
from acbs.crypto import check_hash_hashlib_inner

logger = logging.getLogger(__name__)

build_logging = False
INCLUDE = 0
EXCLUDE = 1

try:
    import pexpect
    build_logging = True
except ImportError:
    pexpect = None

chksum_pattern = re.compile(r"CHKSUM(?:S)?=['\"].*?['\"]", flags=re.MULTILINE | re.DOTALL)
tarball_pattern = re.compile(r'\.(tar\..+|cpio\..+)', flags=re.MULTILINE | re.DOTALL)
SIGNAMES = {k:v for v, k in sorted(signal.__dict__.items(), reverse=True)
                if v.startswith('SIG') and not v.startswith('SIG_')}


def validate_package_name(package_name: str) -> bool:
    """
    Validate package name

    :param package_name: name of the package
    :returns: True if the package name is valid
    """
    if '/' in package_name:
        package_name = os.path.basename(package_name)
    return re.match(r'^[a-z0-9][a-z0-9\-+\.]*$', package_name) is not None


def guess_extension_name_from_contents(filename: str) -> str | None:
    from acbs import magic
    checker = magic.open(magic.MAGIC_MIME_TYPE)
    result = checker.file(filename)
    mime_type = result.decode('utf-8').split(';')[0]
    return {
        "application/zip": "zip",
        "application/gzip": "gz",
        "application/x-xz": "xz",
        "application/vnd.rar": "rar",
        "application/vnd.debian.binary-package": "deb",
        "application/x-7z-compressed": "7z",
        "application/x-xar": "xar",
        "application/x-cpio": "cpio",
    }.get(mime_type)


def guess_extension_name(filename: str) -> str:
    """
    Guess extension name based on filename

    :param filename: name of the file
    :returns: possible extension name
    """
    extension = ''
    # determine the extension name to use
    re_result = re.search(tarball_pattern, filename)
    # handle .tar.* senarios
    if re_result:
        extension = re_result.group(1)
    else:
        # normal single extension name
        extensions = None
        for i in range(len(filename) - 1, -1, -1):
            if filename[i] == '.':
                extensions = filename[i+1:]
                break
        # no extension name?
        if not extensions:
            try:
                return guess_extension_name_from_contents(filename) or ''
            except (OSError, subprocess.CalledProcessError, UnicodeDecodeError):
                return ''
        else:
            # strip out query parameters
            extension = extensions.split('?', 1)[0]
    if extension:
        extension = '.' + extension
    return extension


def get_arch_name() -> str | None:
    """
    Detect architecture of the host machine

    :returns: architecture name
    """
    abcfg_path = os.path.join(AUTOBUILD_CONF_DIR, 'ab4cfg.sh')
    try:
        arch_override = get_arch_override(abcfg_path)
    except (OSError, ParseException):
        arch_override = None
    if arch_override:
        return arch_override
    try:
        output = subprocess.check_output(['dpkg', '--print-architecture'], text=True)
        return output.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def get_archgroups(arch: str | None=None) -> list[str]:
    """
    Get all defined architecture groups for the host machine

    :param arch: When set, fetches all groups containing the specified arch
                 instead of the host macnine.
    :returns: List of the archgroups, such as ['mainline', '64bit'].

    """
    groups = []
    if not arch:
        arch = get_arch_name()
    if not arch:
        return groups

    archgroup_path = Path(AUTOBUILD_DIR) / 'sets' / 'arch_groups.json'
    archgroup_data: dict[str, list[str]] = {}
    try:
        with open(archgroup_path, 'r') as fp:
            data = json.load(fp)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        logger.warning(f"Unable to read arch group data from Autobuild4: {exc}")
        return groups
    if not isinstance(data, dict):
        logger.warning("Invalid arch group data from Autobuild4: expected a JSON object")
        return groups
    archgroup_data.update(data)

    groups.extend([x for x in archgroup_data if arch in archgroup_data[x]])

    return groups

def full_line_banner(msg: str, char='-') -> str:
    """
    Print a full line banner with customizable texts

    :param msg: message you want to be printed
    :param char: character to use to fill the banner
    """
    bars_count = int((shutil.get_terminal_size().columns - len(msg) - 2) / 2)
    bars = char*bars_count
    return f'{bars} {msg} {bars}'


def print_package_names(packages: list[ACBSPackageInfo], limit: int | None = None) -> str:
    """
    Print out the names of packages

    :param packages: list of ACBSPackageInfo objects
    :param limit: maximum number of packages to print
    :return: a string containing the names of the packages
    """
    pkgs = packages
    if limit is not None and len(packages) > limit:
        pkgs = packages[:limit]
    printable_packages = [pkg.name for pkg in pkgs]
    more_messages = f' ... and {len(packages) - limit} more' if limit and limit < len(packages) else ''
    return ', '.join(printable_packages) + more_messages


def make_build_dir(path: str) -> str:
    return tempfile.mkdtemp(dir=path, prefix='acbs.')


def guess_subdir(path: str) -> str | None:
    name = None
    count = 0
    for subdir in os.scandir(path):
        if subdir.is_dir():
            name = subdir.name
            count += 1
        if count > 1:
            return None
    if count < 1:  # probably dummysrc
        name = '.'
    return name


def has_stamp(path: str) -> bool:
    return os.path.exists(os.path.join(path, '.acbs-stamp'))


def start_build_capture(env: dict[str, str], build_dir: str):
    with tempfile.NamedTemporaryFile(prefix='acbs-build_', suffix='.log', dir=build_dir, delete=False) as f:
        logger.info(f'Build log: {f.name}')
        header = f'!!ACBS Build Log\n!!Build start: {time.ctime()}\n'
        f.write(header.encode())
        assert pexpect
        process = pexpect.spawn('autobuild', logfile=f, env=cast(os._Environ, env))
        term_size = shutil.get_terminal_size()
        # we need to adjust the pseudo-terminal size to match the actual screen size
        process.setwinsize(rows=term_size.lines,
                           cols=term_size.columns)
        process.interact()
        # keep killing the process until it finishes
        while (not process.isalive()) and (not process.terminated):
            process.terminate()
        exit_status = process.exitstatus
        signal_status = process.signalstatus
        if signal_status:
            footer = f'\n!!Build killed with {SIGNAMES[signal_status]}'
        else:
            footer = f'\n!!Build exited with {exit_status}'
        f.write(footer.encode())
        if signal_status or exit_status:
            raise RuntimeError('autobuild4 did not exit successfully.')

def start_general_autobuild_metadata(env: dict[str, str], script_location: str, package_name: str, build_dir: str):
    env["AB_WRITE_METADATA"] = "1"
    subprocess.check_call(['autobuild', '-p'], env=env)

    path = ''
    if script_location.split('/')[-1] == 'autobuild':
        path = os.path.join(script_location, '..', '.srcinfo.json')
    else:
        path = os.path.join(script_location, '..', f'.srcinfo-{package_name}.json')

    shutil.copyfile(os.path.join(build_dir, '.srcinfo.json'), path)
    logger.info(f".srcinfo.json saved to: {path}")

def generate_metadata(task: ACBSPackageInfo) -> str:
    tree_commit = 'unknown'
    try:
        tree_commit = subprocess.check_output(
            ['git', '-c', 'safe.directory=/tree', 'describe', '--always', '--dirty'], cwd=task.script_location).decode('utf-8').strip()
    except subprocess.CalledProcessError as ex:
        logger.warning(f'Could not determine tree commit: {ex}')
    return f'X-AOSC-ACBS-Version: {__version__}\nX-AOSC-Commit: {tree_commit}\n'


def generate_version_stamp(task: ACBSPackageInfo) -> str:
    try:
        head_ref = subprocess.check_output(
            ['git', '-c', 'safe.directory=/tree', 'symbolic-ref', 'HEAD'], cwd=task.script_location).decode('utf-8').strip()
        if head_ref == 'refs/heads/stable':
            logger.info('Not using pre-release version stamp')
            return ''

        dirty = len(subprocess.check_output(
            ['git', '-c', 'safe.directory=/tree', 'status', '--porcelain'], cwd=task.script_location).decode('utf-8').strip()) != 0
        timestamp = None
        if dirty:
            timestamp = int(time.time())
        else:
            timestamp = int(subprocess.check_output(
                ['git', '-c', 'safe.directory=/tree', 'show', '-s', '--format=%ct', 'HEAD'], cwd=task.script_location).decode('utf-8').strip())
        stamp = (
            datetime.datetime.fromtimestamp(timestamp, datetime.UTC)
            .strftime('~pre%Y%m%dT%H%M%SZ')
        )
        if dirty:
            stamp += '~dirty'
        logger.info(f'Using version stamp: {stamp}')
        return stamp
    except subprocess.CalledProcessError as ex:
        logger.warning(f'Could not determine version stamp: {ex}')
        return ''


def check_artifact(name: str, build_dir: str):
    """
    Check if the artifact exists

    :param name: name of the package
    :param build_dir: path to the build directory
    """
    for f in os.listdir(build_dir):
        if f.endswith('.deb') and f.startswith(name):
            return
    logger.error(
        f'{ANSI_RED}Autobuild malfunction! Emergency drop!{ANSI_RST}')
    raise RuntimeError(
        'STOP! Autobuild3 malfunction detected! Returned zero status with no artifact.')


def invoke_autobuild(task: ACBSPackageInfo, build_dir: str, stage2: bool, generate_pkg_metadata: bool):
    dst_dir = os.path.join(build_dir, 'autobuild')
    if os.path.exists(dst_dir) and task.group_seq > 1:
        shutil.rmtree(dst_dir)
    shutil.copytree(task.script_location, dst_dir, symlinks=True)
    # Inject variables to defines
    acbs_helper = os.path.join(task.build_location, '.acbs-script')
    env_dict = os.environ.copy()
    env_dict.update({'PKGREL': task.rel, 'PKGVER': task.version,
                     'PKGEPOCH': task.epoch or '0',
                     'VERSTAMP': generate_version_stamp(task)})
    env_dict.update(task.exported)
    if task.modifiers:
        env_dict['ABMODIFIERS'] = task.modifiers
    defines_file = 'defines'
    if stage2 and os.path.exists(os.path.join(build_dir, 'autobuild', 'defines.stage2')):
        defines_file = 'defines.stage2'
    with open(os.path.join(build_dir, 'autobuild', defines_file), 'at') as f:
        f.write(f'\nPKGREL=\'{task.rel}\'\nPKGVER=\'{task.version}\'\nif [ -f \'{acbs_helper}\' ];then source \'{acbs_helper}\' && abinfo "Injected ACBS definitions";fi\n')
        if task.epoch:
            f.write(f'PKGEPOCH=\'{task.epoch}\'')
    with open(os.path.join(build_dir, 'autobuild', 'extra-dpkg-control'), 'wt') as f:
        f.write(generate_metadata(task))
    os.chdir(build_dir)
    if build_logging:
        if not generate_pkg_metadata:
            start_build_capture(env_dict, build_dir)
        else:
            start_general_autobuild_metadata(env_dict, task.script_location, task.name, build_dir)
        return
    logger.warning(
        'Build logging not available due to pexpect not installed.')
    subprocess.check_call(['autobuild'], env=env_dict)


def human_time(full_seconds: float) -> str:
    """
    Convert time span (in seconds) to more friendly format
    :param full_seconds: Time span in seconds (decimal is acceptable)
    """
    if full_seconds < 0:
        return 'Download only'
    out_str_tmp = f'{datetime.timedelta(seconds=full_seconds)}'
    out_str = out_str_tmp.replace(
        ':', f'{ANSI_GREEN}:{ANSI_RST}')
    return out_str


def format_column(data: Sequence[tuple[str, ...]]) -> str:
    col_width = max(len(str(word)) for row in data for word in row)
    return '\n'.join('\t'.join(str(word).ljust(col_width) for word in row) for row in data) + '\n'


def format_package_name(package: ACBSPackageInfo) -> str:
    return f'{package.name} ({package.bin_arch} @ {package.epoch + ":" if package.epoch else ""}{package.version}-{package.rel})'


def print_build_timings(timings: list[tuple[str, float]], failed_packages: list[ACBSPackageInfo], last_build_time: float=0.0):
    """
    Print the build statistics

    :param timings: List of timing data
    """
    formatted_timings: list[tuple[str, str]] = []
    formatted_failed_packages = [format_package_name(pkg) for pkg in failed_packages]
    banner = '=' * 40
    print(f"\n{banner}")
    for timing in timings:
        formatted_timings.append((timing[0], human_time(timing[1])))
    print(f"    ACBS Build {'Successful' if not failed_packages else 'Failed'}")
    print(f"{banner}\n")
    if failed_packages:
        print("Failed package:")
        line_data = (formatted_failed_packages[0], human_time(last_build_time))
        print(format_column([line_data]))
    if timings:
        print("Package(s) built:")
        print(format_column(formatted_timings))
    if len(failed_packages) > 1:
        print("Package(s) not built due to previous build failure:")
        print('\n'.join(formatted_failed_packages[1:]))
        print()


def is_spec_legacy(spec: str) -> bool:
    with open(spec, 'rt') as f:
        content = f.read()
    return content.find('SRCS=') < 0


def generate_checksums(info: list[ACBSSourceInfo], legacy=False) -> str:
    def calculate_checksum(o: ACBSSourceInfo):
        if not o.source_location:
            raise ValueError('source_location is None.')
        csum = check_hash_hashlib_inner('sha256', o.source_location)
        if not csum:
            raise ValueError(
                f'Unable to calculate checksum for {o.source_location}')
        o.chksum = ('sha256', csum)
        return o

    if legacy and info[0].type == 'tarball':
        info[0] = calculate_checksum(info[0])
        return 'CHKSUM=\"{}\"'.format('::'.join(info[0].chksum))
    output = 'CHKSUMS=\"{}\"'
    sums = []
    formatter = ' ' if len(info) < 2 else ' \\\n         '
    for i in info:
        if i.type in ('tarball', 'file', 'pypi'):
            i = calculate_checksum(i)
            sums.append('::'.join(i.chksum))
        else:
            sums.append('SKIP')
    return output.format(formatter.join(sums))


def write_checksums(spec: str, checksums: str):
    with open(spec, 'rt') as f:
        content = f.read()
    if re.search(chksum_pattern, content):
        content = re.sub(chksum_pattern, checksums, content)
    else:
        content = content.rstrip() + "\n" + checksums + "\n"
    with open(spec, 'wt') as f:
        f.write(content)


def fail_arch_regex(expr: str) -> tuple[int, re.Pattern]:
    regex = '^('

    if len(expr) < 3:
        raise ValueError('Pattern too short.')
    mode = EXCLUDE
    # Perform checks
    if expr[0] == '!' and expr[1] == '(':
        mode = EXCLUDE
    elif expr[0] == '@' and expr[1] == '(':
        mode = INCLUDE
    elif re.search('[^0-9a-z_-]', expr) is not None or expr[1:].strip('()') == expr:
        raise ValueError(f'Invalid FAIL_ARCH expression: "{expr}". Refer to bash(1) § Pattern Matching for details.')
    else:
        # Disallow build for one specific archgroup/target.
        return (INCLUDE, re.compile(f'^{expr}$'))
    regex += '|'.join(expr[1:].strip('()').split('|'))
    regex += ')$'
    return (mode, re.compile(regex))


# Check if the package is buildable on current architecture.
def buildable(arch, exp) -> bool:
    mode, regex = fail_arch_regex(exp)
    match_list = get_archgroups(arch)
    match_list.append(arch)
    for entry in match_list:
        if regex.match(entry):
            if mode == INCLUDE:
                return False
            if mode == EXCLUDE:
                return True
    return mode == INCLUDE


class ACBSLogFormatter(logging.Formatter):
    """
    ABBS-like format logger formatter class
    """

    def format(self, record):
        lvl_map = {
            'WARNING': f'{ANSI_BROWN}WARN{ANSI_RST}',
            'INFO': f'{ANSI_LT_CYAN}INFO{ANSI_RST}',
            'DEBUG': f'{ANSI_GREEN}DEBUG{ANSI_RST}',
            'ERROR': f'{ANSI_RED}ERROR{ANSI_RST}',
            'CRITICAL': f'{ANSI_YELLOW}CRIT{ANSI_RST}'
        }
        if record.levelno in (logging.WARNING, logging.ERROR, logging.CRITICAL,
                              logging.INFO, logging.DEBUG):
            record.msg = f'[{lvl_map[record.levelname]}]: \033[1m{record.msg}\033[0m'
        return super().format(record)


class ACBSLogPlainFormatter(logging.Formatter):
    """
    ABBS-like format logger formatter class
    ... but with no color codes
    """

    def format(self, record):
        lvl_map = {
            'WARNING': 'WARN',
            'INFO': 'INFO',
            'DEBUG': 'DEBUG',
            'ERROR': 'ERROR',
            'CRITICAL': 'CRIT'
        }
        if record.levelno in (logging.WARNING, logging.ERROR, logging.CRITICAL,
                              logging.INFO, logging.DEBUG):
            record.msg = f'[{lvl_map[record.levelname]}]: {record.msg}'
        return super().format(record)
