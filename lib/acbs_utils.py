import subprocess


def arr2str(array):
    str_out = ''
    for i in array:
        str_out = str_out + i + ' '
    return str_out.rstrip()


def gen_laundry_list(items):
    # You know what, 'laundry list' can be a joke in somewhere...
    str_out = '\n\n'
    for i in items:
        str_out = str_out + 'echo ' + i + '=' + '\"' + '$' + i + '\"' + '\n'
    return str_out


def test_progs(cmd, display=False):
    try:
        if display == False:
            subprocess.check_output(cmd)
        else:
            subprocess.check_call(cmd)
    except:
        return False

    return True


def check_empty(logic_method, in_dict, in_array):
    '''
logic_method: 1= OR'ed , 2= AND'ed
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
    import platform
    uname_var = platform.machine() or platform.processor()
    if uname_var == 'x86_64' or uname_var == 'amd64':
        return 'amd64'
    elif uname_var == 'aarch64':
        return 'aarch64'  # FIXME: Don't know ...
    elif uname_var.index('arm'):
        return 'armel'
    else:
        return None
    return None


def str_split_to_array(str_in, sep=' '):
    str_arr_a = str_in.split(sep)
    str_arr_b = []
    for i in str_arr_a:
        if i.rstrip() != '':
            str_arr_b.append(i)
    return str_arr_b


def err_msg(desc=None):
    # print('\rTerminated!',sep='')
    # sys.stdout.flush()
    if desc is None:
        print('\n[E] Error occurred! Build terminated.')
    else:
        print(
            '\n[E] Error occurred:\033[93m {} \033[0mBuild terminated.'.format(desc))
    return


def group_match(pattern_list, string, logic_method):
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
