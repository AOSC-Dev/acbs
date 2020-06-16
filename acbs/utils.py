import logging
import shutil
import re
import tempfile
import subprocess
import os
import time
import signal
import datetime

from typing import Optional, List, Tuple, Sequence
from acbs.const import *
from acbs.base import ACBSPackageInfo

build_logging = False

try:
    import pexpect  # type: ignore
    build_logging = True
except ImportError:
    pass

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
        extensions = filename.split('.', 1)
        # no extension name?
        if len(extensions) != 2:
            return ''
        else:
            # strip out query parameters
            extension = extensions[1].split('?', 1)[0]
    if extension:
        extension = '.' + extension
    return extension


def get_arch_name() -> Optional[str]:
    """
    Detect architecture of the host machine

    :returns: architecture name
    """
    import platform
    uname_var = platform.machine() or platform.processor()
    return {
            'x86_64': 'amd64',
            'i486': 'i486',
            'i686': 'i686',
            'armv7l': 'armel',
            'armv8l': 'armel',
            'aarch64': 'arm64',
            'ppc': 'powerpc',
            'ppc64': 'ppc64',
            'ppc64le': 'ppc64el',
            'riscv64': 'riscv64',
            'mips64': 'mips64r2el'
        }.get(uname_var) or uname_var


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


def start_build_capture(build_dir: str):
    with tempfile.NamedTemporaryFile(prefix='acbs-build_', suffix='.log', dir=build_dir, delete=False) as f:
        logging.info('Build log: %s' % f.name)
        header = '!!ACBS Build Log\n!!Build start: %s\n' % time.ctime()
        f.write(header.encode())
        process = pexpect.spawn('autobuild', logfile=f)
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
            footer = '\n!!Build killed with %s' % SIGNAMES[signal_status]
        else:
            footer = '\n!!Build exited with %s' % exit_status
        f.write(footer.encode())
        if signal_status or exit_status:
            raise RuntimeError('autobuild3 did not exit successfully.')


def invoke_autobuild(task: ACBSPackageInfo, build_dir: str):
    dst_dir = os.path.join(build_dir, 'autobuild')
    if os.path.exists(dst_dir) and task.group_seq > 1:
        shutil.rmtree(dst_dir)
    shutil.copytree(task.script_location, dst_dir, symlinks=True)
    # Inject variables to defines
    acbs_helper = os.path.join(task.build_location, '.acbs-script')
    with open(os.path.join(build_dir, 'autobuild', 'defines'), 'at') as f:
        f.write('\nPKGREL=\'{}\'\nPKGVER=\'{}\'\n[ -f \'{}\' ] && source \'{}\' && abinfo "Injected ACBS definitions"\n'.format(
            task.rel, task.source_uri.version, acbs_helper, acbs_helper))
    os.chdir(build_dir)
    if build_logging:
        start_build_capture(build_dir)
        return
    logging.warning(
        'Build logging not available due to pexpect not installed.')
    subprocess.check_call(['autobuild'])


def human_time(full_seconds: float) -> str:
    """
    Convert time span (in seconds) to more friendly format
    :param seconds: Time span in seconds (decimal is acceptable)
    """
    out_str_tmp = '{}'.format(
        datetime.timedelta(seconds=full_seconds))
    out_str = out_str_tmp.replace(
        ':', ('{}:{}'.format(ANSI_GREEN, ANSI_RST)))
    return out_str


def format_column(data: Sequence[Tuple[str, ...]]) -> str:
    output = ''
    col_width = max(len(str(word)) for row in data for word in row)
    for row in data:
        output = '%s%s\n' % (
            output, ('\t'.join(str(word).ljust(col_width) for word in row)))
    return output


def print_build_timings(timings: List[Tuple[str, float]]):
    formatted_timings: List[Tuple[str, str]] = []
    for timing in timings:
        formatted_timings.append((timing[0], human_time(timing[1])))
    print(full_line_banner('Build Summary'))
    print(format_column(formatted_timings))


class ACBSLogFormatter(logging.Formatter):
    """
    ABBS-like format logger formatter class
    """

    def format(self, record):
        lvl_map = {
            'WARNING': '{}WARN{}'.format(ANSI_BROWN, ANSI_RST),
            'INFO': '{}INFO{}'.format(ANSI_LT_CYAN, ANSI_RST),
            'DEBUG': '{}DEBUG{}'.format(ANSI_GREEN, ANSI_RST),
            'ERROR': '{}ERROR{}'.format(ANSI_RED, ANSI_RST),
            'CRITICAL': '{}CRIT{}'.format(ANSI_YELLOW, ANSI_RST)
        }
        if record.levelno in (logging.WARNING, logging.ERROR, logging.CRITICAL,
                              logging.INFO, logging.DEBUG):
            record.msg = '[%s]: %s' % (lvl_map[record.levelname], record.msg)
        return super(ACBSLogFormatter, self).format(record)
