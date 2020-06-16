import logging
import shutil
import re
import tempfile
import subprocess
import os
import time
import signal

from typing import Optional, List
from acbs.const import *
from acbs.base import ACBSPackageInfo

build_logging = False

try:
    import pexpect
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
    if uname_var in ['x86_64', 'amd64']:
        return 'amd64'
    elif uname_var in ['armv7a', 'armv7l', 'armv8a', 'armv8l']:
        return 'armel'
    else:
        return {
            'aarch64': 'arm64',
            'mips64': 'mips64el',  # FIXME: How about big endian...
            'mips': 'mipsel',  # FIXME: This too...
            'ppc': 'powerpc',
            'ppc64': 'ppc64',
            'riscv64': 'riscv64'
        }.get(uname_var)


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


def start_build_capture(build_dir: str):
    with tempfile.NamedTemporaryFile(prefix='acbs-build_', suffix='.log', dir=build_dir, delete=False) as f:
        logging.info('Build log: %s' % f.name)
        header = '!!ACBS Build Log\n!!Build start: %s\n' % time.ctime()
        f.write(header.encode())
        process = pexpect.spawn('wget', logfile=f)
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
    shutil.copytree(task.script_location, os.path.join(build_dir, 'autobuild'))
    # Inject variables to defines
    with open(os.path.join(build_dir, 'autobuild', 'defines'), 'at') as f:
        f.write('\nPKGREL=\'{}\'\nPKGVER=\'{}\'\n'.format(
            task.rel, task.source_uri.version))
    os.chdir(build_dir)
    if build_logging:
        start_build_capture(build_dir)
        return
    logging.warning(
        'Build logging not available due to pexpect not installed.')
    subprocess.check_call(['autobuild'])


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
