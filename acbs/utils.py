import datetime
import logging
import os
import re
import shutil
import signal
import subprocess
import tempfile
import time
from typing import List, Optional, Sequence, Tuple, Dict

from acbs.base import ACBSPackageInfo, ACBSSourceInfo
from acbs.crypto import check_hash_hashlib_inner
from acbs.const import (ANSI_BROWN, ANSI_GREEN, ANSI_LT_CYAN, ANSI_RED,
                        ANSI_RST, ANSI_YELLOW)
from acbs import __version__

build_logging = False

try:
    import pexpect  # type: ignore
    build_logging = True
except ImportError:
    pass

chksum_pattern = r"CHKSUM(?:S)?=['\"].*?['\"]"
tarball_pattern = r'\.(tar\..+|cpio\..+)'
SIGNAMES = dict((k, v) for v, k in reversed(sorted(signal.__dict__.items()))
                if v.startswith('SIG') and not v.startswith('SIG_'))


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
            return ''
        else:
            # strip out query parameters
            extension = extensions.split('?', 1)[0]
    if extension:
        extension = '.' + extension
    return extension


def get_arch_name() -> Optional[str]:
    """
    Detect architecture of the host machine

    :returns: architecture name
    """
    try:
        output = subprocess.check_output(['dpkg', '--print-architecture'])
        return output.decode('utf-8').strip()
    except Exception:
        return None
    return None


def full_line_banner(msg: str, char='-') -> str:
    """
    Print a full line banner with customizable texts

    :param msg: message you want to be printed
    :param char: character to use to fill the banner
    """
    bars_count = int((shutil.get_terminal_size().columns - len(msg) - 2) / 2)
    bars = char*bars_count
    return ' '.join((bars, msg, bars))


def print_package_names(packages: List[ACBSPackageInfo], limit: Optional[int] = None) -> str:
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
    more_messages = ' ... and {} more'.format(
        len(packages) - limit) if limit and limit < len(packages) else ''
    return ', '.join(printable_packages) + more_messages


def make_build_dir(path: str) -> str:
    return tempfile.mkdtemp(dir=path, prefix='acbs.')


def guess_subdir(path: str) -> Optional[str]:
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


def start_build_capture(env: Dict[str, str], build_dir: str):
    with tempfile.NamedTemporaryFile(prefix='acbs-build_', suffix='.log', dir=build_dir, delete=False) as f:
        logging.info(f'Build log: {f.name}')
        header = f'!!ACBS Build Log\n!!Build start: {time.ctime()}\n'
        f.write(header.encode())
        process = pexpect.spawn('autobuild', logfile=f, env=env)
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
            raise RuntimeError('autobuild3 did not exit successfully.')


def generate_metadata(task: ACBSPackageInfo) -> str:
    tree_commit = 'unknown'
    try:
        tree_commit = subprocess.check_output(
            ['git', 'describe', '--always', '--dirty'], cwd=task.script_location).decode('utf-8')
    except subprocess.CalledProcessError as ex:
        logging.warning(f'Could not determine tree commit: {ex}')
    return f'X-AOSC-ACBS-Version: {__version__}\nX-AOSC-Commit: {tree_commit}'


def check_artifact(name: str, build_dir: str):
    """
    Check if the artifact exists

    :param name: name of the package
    :param build_dir: path to the build directory
    """
    for f in os.listdir(build_dir):
        if f.endswith('.deb') and f.startswith(name):
            return
    logging.error(
        f'{ANSI_RED}Autobuild malfunction! Emergency drop!{ANSI_RST}')
    raise RuntimeError(
        'STOP! Autobuild3 malfunction detected! Returned zero status with no artifact.')


def invoke_autobuild(task: ACBSPackageInfo, build_dir: str, stage2: bool):
    dst_dir = os.path.join(build_dir, 'autobuild')
    if os.path.exists(dst_dir) and task.group_seq > 1:
        shutil.rmtree(dst_dir)
    shutil.copytree(task.script_location, dst_dir, symlinks=True)
    # Inject variables to defines
    acbs_helper = os.path.join(task.build_location, '.acbs-script')
    env_dict = os.environ.copy()
    env_dict.update({'PKGREL': task.rel, 'PKGVER': task.version,
                     'PKGEPOCH': task.epoch or '0'})
    env_dict.update(task.exported)
    defines_file = 'defines'
    if stage2 and os.path.exists(os.path.join(build_dir, 'autobuild', 'defines.stage2')):
        defines_file = 'defines.stage2'
    with open(os.path.join(build_dir, 'autobuild', defines_file), 'at') as f:
        f.write('\nPKGREL=\'{}\'\nPKGVER=\'{}\'\nif [ -f \'{}\' ];then source \'{}\' && abinfo "Injected ACBS definitions";fi\n'.format(
            task.rel, task.version, acbs_helper, acbs_helper))
        if task.epoch:
            f.write(f'PKGEPOCH=\'{task.epoch}\'')
    with open(os.path.join(build_dir, 'autobuild', 'extra-dpkg-control'), 'wt') as f:
        f.write(generate_metadata(task))
    os.chdir(build_dir)
    if build_logging:
        start_build_capture(env_dict, build_dir)
        return
    logging.warning(
        'Build logging not available due to pexpect not installed.')
    subprocess.check_call(['autobuild'], env=env_dict)


def human_time(full_seconds: float) -> str:
    """
    Convert time span (in seconds) to more friendly format
    :param full_seconds: Time span in seconds (decimal is acceptable)
    """
    if full_seconds < 0:
        return 'Download only'
    out_str_tmp = '{}'.format(
        datetime.timedelta(seconds=full_seconds))
    out_str = out_str_tmp.replace(
        ':', f'{ANSI_GREEN}:{ANSI_RST}')
    return out_str


def format_column(data: Sequence[Tuple[str, ...]]) -> str:
    output = ''
    col_width = max(len(str(word)) for row in data for word in row)
    for row in data:
        output = '%s%s\n' % (
            output, ('\t'.join(str(word).ljust(col_width) for word in row)))
    return output


def print_build_timings(timings: List[Tuple[str, float]], failed_packages: List[str]):
    """
    Print the build statistics

    :param timings: List of timing data
    """
    formatted_timings: List[Tuple[str, str]] = []
    print(full_line_banner('', '='))
    for timing in timings:
        formatted_timings.append((timing[0], human_time(timing[1])))
    print('\t\tACBS Build {}', 'Successful' if not failed_packages else 'Failed')
    print(full_line_banner('', '='))
    if failed_packages:
        print("Failed package:")
        print(failed_packages[0])
    if timings:
        print("Package(s) built:")
        print(format_column(formatted_timings))
    if len(failed_packages) > 2:
        print("Package(s) not built due to previous build failure:")
        print(failed_packages[1:])


def is_spec_legacy(spec: str) -> bool:
    with open(spec, 'rt') as f:
        content = f.read()
    return content.find('SRCS=') < 0


def generate_checksums(info: List[ACBSSourceInfo], legacy=False) -> str:
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
        if i.type in ('tarball', 'file'):
            i = calculate_checksum(i)
            sums.append('::'.join(i.chksum))
        else:
            sums.append('SKIP')
    return output.format(formatter.join(sums))


def write_checksums(spec: str, checksums: str):
    with open(spec, 'rt') as f:
        content = f.read()
    if re.search(chksum_pattern, content, re.MULTILINE | re.DOTALL):
        content = re.sub(chksum_pattern, checksums, content,
                         flags=re.MULTILINE | re.DOTALL)
    else:
        content = content.rstrip() + "\n" + checksums + "\n"
    with open(spec, 'wt') as f:
        f.write(content)
    return


def fail_arch_regex(expr: str) -> re.Pattern:
    regex = '^'
    negated = False
    sup_bracket = False
    if len(expr) < 3:
        raise ValueError('Pattern too short.')
    for i, c in enumerate(expr):
        if i == 0 and c == '!':
            negated = True
            if expr[1] != '(':
                regex += '('
                sup_bracket = True
            continue
        if negated:
            if c == '(':
                regex += '(?!'
                continue
            elif i == 1 and sup_bracket:
                regex += '?!'
        regex += c
    if sup_bracket:
        regex += ')'
    return re.compile(regex)


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
        return super(ACBSLogFormatter, self).format(record)


class ACBSLogPlainFormatter(logging.Formatter):
    """
    ABBS-like format logger formatter class
    ... but with no color codes
    """

    def format(self, record):
        lvl_map = {
            'WARNING': f'WARN',
            'INFO': f'INFO',
            'DEBUG': f'DEBUG',
            'ERROR': f'ERROR',
            'CRITICAL': f'CRIT'
        }
        if record.levelno in (logging.WARNING, logging.ERROR, logging.CRITICAL,
                              logging.INFO, logging.DEBUG):
            record.msg = f'[{lvl_map[record.levelname]}]: {record.msg}'
        return super(ACBSLogFormatter, self).format(record)
