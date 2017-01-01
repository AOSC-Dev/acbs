import subprocess
import logging
import sys
import traceback
from acbs import const

LOGIC_OR = 1
LOGIC_AND = 2


def list2str(list_in, sep=' '):
    """
    A simple conversion function to format `list` to `string` with given \
    seperator

    :param list_in: A list that needed to be formatted
    :param sep: Seperator, default is a single non-breaking space `' '`
    :returns: A formatted string
    :raises TypeError: `list_in` must be of `list` type
    """
    return sep.join(map(str, list_in))


def gen_laundry_list(items):
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


def test_progs(cmd, display=False):
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
            _, _ = proc.communicate()  # Maybe one day we'll need its output...?
        else:
            subprocess.check_call(cmd)
    except Exception:
        return False

    return True


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
            if in_dict[i] == '' or in_dict[i] is None:
                return True  # This is empty
    elif logic_method == 1:
        for i in in_array:
            if in_dict[i] != '' and in_dict[i] is not None:
                return False
        return True
    else:
        raise ValueError('Value of logic_method is illegal!')
    return False


def get_arch_name():
    """
    Detect architecture of the host machine

    :returns: architecture name
    """
    import platform
    uname_var = platform.machine() or platform.processor()
    if uname_var in ['x86_64', 'amd64']:
        return 'amd64'
    elif uname_var == 'aarch64':
        return 'aarch64'  # FIXME: Don't know ...
    elif uname_var.index('arm'):
        return 'armel'    # FIXME: Don't know too much about this...
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
    # print('\rTerminated!',sep='')
    # sys.stdout.flush()
    if desc is None:
        print('\n')
        logging.error('Error occurred! Build terminated.')
    else:
        print('\n')
        logging.error(
            'Error occurred:\033[93m {} \033[0mBuild terminated.'.format(desc))
    return


def group_match(pattern_list, string, logic_method):
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
        return False


def full_line_banner(msg):
    import shutil
    bars_count = int((shutil.get_terminal_size().columns - len(msg)) / 2)
    for i in range(0, bars_count):
        msg = '-{}-'.format(msg)
    return msg


def random_msg():

    return ''


def sh_executor(sh_file, function, args, display=False):
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
        outs, errs = subprocess.Popen(
            ('bash',), stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE).communicate(excute_code.encode('utf-8'))
    return outs.decode('utf-8')


def acbs_terminate(exit_code):
    sys.exit(exit_code)
    return


def time_this(desc_msg):
    def time_this_func(func):
        def dec_main(*args, **kwargs):
            import time
            now_time = time.time()
            ret = func(*args, **kwargs)
            time_span = time.time() - now_time
            logging.info(
                '>>>>>>>>> %s : %s' % (desc_msg, human_time(time_span)))
            return ret
        return dec_main
    return time_this_func


def human_time(full_seconds):
    import datetime
    out_str_tmp = '{}'.format(
        datetime.timedelta(seconds=full_seconds))
    out_str = out_str_tmp.replace(
        ':', ('{}:{}'.format(const.ANSI_GREEN, const.ANSI_RST)))
    return out_str


class ACBSLogFormatter(logging.Formatter):
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
            record.msg = '[%s] %s' % (lvl_map[record.levelname], record.msg)
        return super(ACBSLogFormatter, self).format(record)


class ACBSConfError(Exception):
    pass


class ACBSGeneralError(Exception):
    pass
