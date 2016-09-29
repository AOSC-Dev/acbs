import subprocess
import logging
import sys
from lib.acbs_const import acbs_const


class acbs_utils(object):

    def list2str(list_in, sep=' '):
        """
        A simple conversion function to format `list` to `string` with given \
        seperator

        :param list_in: A list that needed to be formatted
        :param sep: Seperator, default is a single non-breaking space `' '`
        :returns: A formatted string
        :raises TypeError: `list_in` must be of `list` type
        """
        return sep.join(list_in)

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
            str_out = str_out + 'echo \"%s\"=\"${%s}\"\n' % (i, i)
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
        except:
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
        str_list_a = str_in.split(sep)
        str_list_b = []
        for i in str_list_a:
            if i.rstrip() != '':
                str_list_b.append(i)
        return str_list_b

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

    def random_msg():

        return ''

    def sh_executor(self, file, function, args, display=False):
        """
        Execute specified functions in external shell scripts with given args

        :param file: The full path to the script file
        :param function: The function need to be excute_code
        :param: args: The arguments that need to be passed to the function
        :param display: Wether return script output or display on screen
        :returns: Return if excution succeeded or return output per requested
        :raise FileNotFoundError: If script file doesn't exist, raise this.
        """
        with open(file, 'rt') as f:
            sh_code = f.read()
        excute_code = '%s\n%s %s\n' % (sh_code, function, args)
        try:
            if display:
                subprocess.check_call(excute_code, shell=True)
                return True
            else:
                output = subprocess.check_output(
                    excute_code, shell=True, stderr=subprocess.STDOUT)
            return output.decode('utf-8')
        except:
            return None
        return None

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
                    '>>>>>>>>> %s : %s' % (desc_msg, acbs_utils.human_time(time_span)))
                return ret
            return dec_main
        return time_this_func

    def human_time(full_seconds):
        acc = acbs_const()
        import math
        out_str = ''
        msec, seconds = math.modf(full_seconds)
        if seconds >= 86400:  # 86400 = 24 * 3600
            days = int(seconds / 86400)
            seconds = (seconds % 86400)
            if days > 1:
                pl = 's'
            else:
                pl = ''
            out_str += '%s%s%s %sday%s%s, ' % (acc.ANSI_LT_CYAN,
                                               days, acc.ANSI_RST, acc.ANSI_GREEN, pl, acc.ANSI_RST)
        if seconds >= 3600:
            hrs = int(seconds / 3600)
            seconds = (seconds % 3600)
            out_str += '%s%s%s %sh%s ' % (acc.ANSI_LT_CYAN,
                                          hrs, acc.ANSI_RST, acc.ANSI_GREEN, acc.ANSI_RST)
        if seconds >= 60:
            mins = int(seconds / 60)
            seconds = (seconds % 60)
            out_str += '%s%s%s %sm%s ' % (acc.ANSI_LT_CYAN,
                                          mins, acc.ANSI_RST, acc.ANSI_GREEN, acc.ANSI_RST)
        if seconds > 0:
            out_str += '%s%s%s %ss%s ' % (acc.ANSI_LT_CYAN,
                                          int(seconds), acc.ANSI_RST, acc.ANSI_GREEN, acc.ANSI_RST)
        if msec > 0.0:
            out_str += '%s%s%s %sms%s ' % (acc.ANSI_LT_CYAN,
                                           int(msec * 1000), acc.ANSI_RST, acc.ANSI_GREEN, acc.ANSI_RST)
        return out_str


class acbs_log_format(logging.Formatter):
    """
    ABBS-like format logger formatter class
    """

    def format(self, record):
        # FIXME: Let's come up with a way to simplify this ****
        acc = acbs_const()
        lvl_map = {
            'WARNING': '{}WARN{}'.format(acc.ANSI_BROWN, acc.ANSI_RST),
            'INFO': '{}INFO{}'.format(acc.ANSI_LT_CYAN, acc.ANSI_RST),
            'DEBUG': '{}DEBUG{}'.format(acc.ANSI_GREEN, acc.ANSI_RST),
            'ERROR': '{}ERROR{}'.format(acc.ANSI_RED, acc.ANSI_RST),
            'CRITICAL': '{}CRIT{}'.format(acc.ANSI_YELLOW, acc.ANSI_RST)
            # 'FATAL': '{}{}WTF{}'.format(acc.ANSI_BLNK, acc.ANSI_RED, acc.ANSI_RST),
        }
        if record.levelno in (logging.WARNING, logging.ERROR, logging.CRITICAL, logging.INFO,
                              logging.DEBUG):
            record.msg = '[%s] %s' % (lvl_map[record.levelname], record.msg)
        return super(acbs_log_format, self).format(record)
