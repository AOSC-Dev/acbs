import subprocess
import logging
import re
import sys
from acbs import const

LOGIC_OR = 1
LOGIC_AND = 2


def uniq(seq: list) -> list:  # Dave Kirby
    # Order preserving
    """
    An order preserving de-duplicator by Dave Kirby

    :param seq: The list you want to de-duplicate
    :returns: De-duplicated list
    """
    seen = set()
    return [x for x in seq if x not in seen and not seen.add(x)]


def list2str(list_in: list, sep=' ') -> str:
    """
    A simple conversion function to format `list` to `string` with given \
    seperator

    :param list_in: A list that needed to be formatted
    :param sep: Seperator, default is a single non-breaking space `' '`
    :returns: A formatted string
    :raises TypeError: `list_in` must be of `list` type
    """
    return sep.join(map(str, list_in))


def gen_laundry_list(items: list) -> str:
    """
    Generate a laundry list for Bash to interpret

    :param items: An array representing objects that needed to be collected \
    and interpreted
    :returns: A string which is a small Bash snipplet for interpreting.
    """
    # You know what, 'laundry list' can be a joke in somewhere...
    str_out = '\n\n'
    for i in items:
        str_out += 'echo \"%s\"=\"${%s}\"\n' % (i, i)
        # For example: `echo "VAR"="${VAR}"\n`
    return str_out


def test_progs(cmd, display=False) -> bool:
    """
    Test if the given external program can run without flaw

    :param cmd: A list, the command-line arguments
    :param display: Whether to be displayed in the terminal
    :returns: Whether the external program exited successfully
    """
    try:
        if display is False:
            # _ = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
            proc = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            _, _ = proc.communicate()
            # Maybe one day we'll need its output...?
        else:
            subprocess.check_call(cmd)
    except Exception:
        return False

    return True


def merge_dicts(*dict_args):
    '''
    Given any number of dicts, shallow copy and merge into a new dict, \
    precedence goes to key value pairs in latter dicts.
    '''
    result = {}
    for dictionary in dict_args:
        result.update(dictionary)
    return result


def check_empty(logic_method, in_dict, in_array):
    '''
    A simple function to check if objects in a `dict` is empty

    :param logic_method: 1= OR'ed , 2= AND'ed
    :param in_dict: Input dictionary object
    :param in_array: The selected values to be tested against
    :returns: A Boolean, the test result
    '''
    if logic_method == 2:
        for i in in_array:
            if not in_dict.get(i):
                return True  # This is empty
    elif logic_method == 1:
        for i in in_array:
            if in_dict.get(i):
                return False
        return True
    else:
        raise ValueError('Value of logic_method is illegal!')
    return False


def get_arch_name() -> str:
    """
    Detect architecture of the host machine

    :returns: architecture name
    """
    import platform
    uname_var = platform.machine() or platform.processor()
    if uname_var in ['x86_64', 'amd64']:
        return 'amd64'
    elif uname_var == 'aarch64':
        return 'arm64'  # FIXME: Don't know ...
    elif uname_var in ['armv7a', 'armv7l', 'armv8a', 'armv8l']:
        return 'armel'    # FIXME: Don't know too much about this...
    elif uname_var == 'mips64':
        return 'mips64el'  # FIXME: How about big endian...
    elif uname_var == 'mips':
        return 'mipsel'   # FIXME: This too...
    elif uname_var == 'ppc':
        return 'powerpc'
    elif uname_var == 'ppc64':
        return 'ppc64'
    elif uname_var == 'riscv64':
        return 'riscv64'
    else:
        return None
    return None


def str_split_to_list(str_in, sep=' '):
    """
    A simple stupid function to split strings

    :param str_in: A string to be splitted
    :param sep: Seperator
    :returns: A list
    """
    return list(filter(None, str_in.split(sep)))


def err_msg(desc=None):
    """
    Print error message

    :param desc: description of the error message
    """
    if desc is None:
        print('\n')
        logging.error('Error occurred!')
    else:
        print('\n')
        logging.error(
            'Error occurred:\033[93m {} \033[0m'.format(desc))


def group_match(pattern_list: list, string: str, logic_method: int) -> bool:
    """
    Match multiple patterns in one go.

    :param pattern_list: A list contains patterns to be used
    :param string: A string to be tested against
    :param logic_method: 1= OR'ed logic, 2= AND'ed logic
    :returns: Boolean, the test result
    :raises ValueError: pattern_list should be a `list` object, and \
    logic_method should be 1 or 2.
    """
    import re
    if not isinstance(pattern_list, list):
        raise ValueError()
    if logic_method == 1:
        for i in pattern_list:
            if re.match(i, string):
                return True
        return False
    elif logic_method == 2:
        for i in pattern_list:
            if not re.match(i, string):
                return False
        return True
    else:
        raise ValueError('...')


def full_line_banner(msg, char='-'):
    """
    Print a full line banner with customizable texts

    :param msg: message you want to be printed
    """
    import shutil
    bars_count = int((shutil.get_terminal_size().columns - len(msg) - 2) / 2)
    bars = char*bars_count
    return ' '.join((bars, msg, bars))


def random_msg():

    return ''


def sh_executor(sh_file: str, function: str, args: list, display=False) -> bool:
    """
    Execute specified functions in external shell scripts with given args

    :param file: The full path to the script file
    :param function: The function need to be excute_code
    :param: args: The arguments that need to be passed to the function
    :param display: Wether return script output or display on screen
    :returns: Return if excution succeeded or return output per requested
    :raise FileNotFoundError: If script file doesn't exist, raise this.
    """
    with open(sh_file, 'rt') as f:
        sh_code = f.read()
    excute_code = '%s\n%s %s\n' % (sh_code, function, args)
    if display:
        try:
            subprocess.check_call(excute_code, shell=True)
        except subprocess.CalledProcessError:
            return False
        return True
    else:
        outs, _ = subprocess.Popen(
            ('bash',), stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE).communicate(excute_code.encode('utf-8'))
    return outs.decode('utf-8')


def acbs_terminate(exit_code: int) -> None:
    sys.exit(exit_code)


def time_this(desc_msg: str, vars_ctx=None):
    def time_this_func(func):
        def dec_main(*args, **kwargs):
            import time
            now_time = time.time()
            ret = func(*args, **kwargs)
            time_span = time.time() - now_time
            if vars_ctx:
                if not vars_ctx.get('timings'):
                    vars_ctx.set('timings', [time_span])
                else:
                    vars_ctx.get('timings').append(time_span)
            logging.info(
                '>>>>>>>>> %s: %s' % (desc_msg, human_time(time_span)))
            return ret
        return dec_main
    return time_this_func


def human_time(full_seconds: float) -> str:
    """
    Convert time span (in seconds) to more friendly format

    :param seconds: Time span in seconds (decimal is acceptable)
    """
    import datetime
    out_str_tmp = '{}'.format(
        datetime.timedelta(seconds=full_seconds))
    out_str = out_str_tmp.replace(
        ':', ('{}:{}'.format(const.ANSI_GREEN, const.ANSI_RST)))
    return out_str


def format_column(data: list) -> str:
    output = ''
    col_width = max(len(str(word)) for row in data for word in row)
    for row in data:
        output = '%s%s\n' % (
            output, ('\t'.join(str(word).ljust(col_width) for word in row)))
    return output


def format_packages(*packages):
    return ', '.join('\033[36m%s\033[0m' % p for p in packages)


class ACBSVariables(object):

    buffer = {}

    def __init__(self):
        return

    @classmethod
    def get(cls, var_name):
        return cls.buffer.get(var_name)

    @classmethod
    def set(cls, var_name, value):
        cls.buffer[var_name] = value
        return


class ACBSColorFormatter(logging.Formatter):
    """
    ABBS-like format logger formatter class
    """

    def format(self, record):
        # FIXME: Let's come up with a way to simplify this ****
        lvl_map = {
            'WARNING': '{}WARN{}'.format(const.ANSI_BROWN, const.ANSI_RST),
            'INFO': '{}INFO{}'.format(const.ANSI_LT_CYAN, const.ANSI_RST),
            'DEBUG': '{}DEBUG{}'.format(const.ANSI_GREEN, const.ANSI_RST),
            'ERROR': '{}ERROR{}'.format(const.ANSI_RED, const.ANSI_RST),
            'CRITICAL': '{}CRIT{}'.format(const.ANSI_YELLOW, const.ANSI_RST)
            # 'FATAL': '{}{}WTF{}'.format(const.ANSI_BLNK, const.ANSI_RED,
            # const.ANSI_RST),
        }
        if record.levelno in (logging.WARNING, logging.ERROR, logging.CRITICAL,
                              logging.INFO, logging.DEBUG):
            record.colorlevelname = lvl_map[record.levelname]
        return super(ACBSColorFormatter, self).format(record)


class ACBSTextLogFormatter(logging.Formatter):
    """
    Formatter class for stripping color codes
    """
    re_ansi = re.compile('\x1B\\[([0-9]{1,2}(;[0-9]{1,2})?)?[mGK]')

    def format(self, record):
        record.msg = self.re_ansi.sub('', record.msg)
        return super().format(record)


class ACBSConfError(Exception):
    pass


class ACBSGeneralError(Exception):
    pass
