import subprocess
import os

from lib.acbs_src_process import src_proc_dispatcher
from lib.acbs_utils import test_progs, err_msg

dump_loc = '/var/cache/acbs/tarballs/'  # Currently hard-coded


def src_dispatcher(pkg_info):
    if pkg_info['DUMMYSRC'] != '':
        print('[I] Not fetching dummy source as required.')
        return True
    if pkg_info['SRCTBL'] != '':
        src_url = pkg_info['SRCTBL']
        return src_url_dispatcher(src_url, pkg_info)
    if pkg_info['GITSRC'] != '':
        return src_git_fetch(pkg_info['GITSRC'], pkg_info)
    if pkg_info['SVNSRC'] != '':
        return src_svn_fetch(pkg_info['SVNSRC'], pkg_info)
    if pkg_info['HGSRC'] != '':
        return src_hg_fetch(pkg_info['HGSRC'], pkg_info)
    if pkg_info['BZRSRC'] != '':
        return src_bzr_fetch(pkg_info['BZRSRC'], pkg_info)
    return True


def src_url_dispatcher(url, pkg_info):
    # url_array = url.split('\n').split(' ') #for future usage
    pkg_name = pkg_info['NAME']
    pkg_ver = pkg_info['VER']
    try:
        proto = url.split('://')[0].lower()
    except:
        print('[E] Illegal source URL!!!')
        return False
    if proto == 'http' or proto == 'https' or proto == 'ftp' or proto == 'ftps' or proto == 'ftpes':
        src_tbl_name = pkg_name + '-' + pkg_ver
        src_name = os.path.basename(url)
        if src_tbl_fetch(url, src_tbl_name):
            return src_proc_dispatcher(pkg_name, src_name, dump_loc)
    elif proto == 'git':  # or proto == 'git+https'
        print('[W] In spec file: This source seems like a Git repository, while\
         you misplaced it.')
        if src_git_fetch(url, pkg_info):
            return src_proc_dispatcher(pkg_name, pkg_name, dump_loc)
    elif proto == 'hg':
        if src_hg_fetch(url, pkg_info):
            return src_proc_dispatcher(pkg_name, pkg_name, dump_loc)
    elif proto == 'svn':
        if src_svn_fetch(url, pkg_info):
            return src_proc_dispatcher(pkg_name, pkg_name, dump_loc)
    elif proto == 'bzr':
        if src_bzr_fetch(url, pkg_info):
            return src_proc_dispatcher(pkg_name, pkg_name, dump_loc)
    else:
        print('[E] Unknown protocol {}'.format(proto))
        return False
    return False


def src_git_fetch(url, pkg_info):
    if not test_progs(['git', '--version']):
        print('[E] Git is not installed!')
        return False
    if pkg_info['GITSRC'] == '':
        print('[E] Source URL is empty!')
        return False
    if pkg_info['GITCO'] == '':
        print('[W] Source revision not specified! Will use HEAD commit instead!')
    print('[I] Cloning Git repository...')
    os.chdir(dump_loc)
    try:
        if os.path.isdir(pkg_info['NAME']) and os.path.isdir(pkg_info['NAME']+'/.git'):
            os.chdir(pkg_info['NAME'])
            print('[I] Updating existing repository...')
            # subprocess.check_call(['git', 'pull', '-f'])
        else:
            subprocess.check_call(['git', 'clone', pkg_info['GITSRC'], pkg_info['NAME']])
            os.chdir(pkg_info['NAME'])
        if pkg_info['GITBRCH'] != '':
            subprocess.check_call(['git', 'checkout', '-f', pkg_info['GITBRCH']])
        if pkg_info['GITCO'] != '':
            subprocess.check_call(['git', 'checkout', '-f', pkg_info['GITCO']])
    except:
        print('[E] Failed to fetch source!')
        return False
    return src_proc_dispatcher(pkg_info['NAME'], pkg_info['NAME'], dump_loc)


def src_tbl_fetch(url, pkg_slug):
    use_progs = test_downloaders()
    src_name = os.path.basename(url)
    full_path = os.path.join(dump_loc, src_name)
    flag_file = full_path + '.dl'
    if os.path.exists(full_path) and (not os.path.exists(flag_file)):
        return True
    fp = open(flag_file, 'wt')
    fp.write('acbs flag: DO NOT DELETE!')
    fp.close()
    for i in use_progs:
        try:
            # print('{}_get({}, output={})'.format(i, url, full_path))
            exec('{}_get(\'{}\', output=\'{}\')'.format(i, url, full_path))
            os.unlink(flag_file)
            break
        except KeyboardInterrupt:
            err_msg('You aborted the download!')
            return False
        except NameError:
            raise NameError('An Internal Error occurred!')
        except AssertionError:
            continue
        except:
            return False
    return True


def src_svn_fetch(url, pkg_info):
    if not test_progs(['svn', '-h']):
        print('[E] Subverion is not installed!')
        return False
    if pkg_info['SVNSRC'] == '':
        print('[E] Source URL is empty!')
        return False
    if pkg_info['SVNCO'] == '':
        print('[W] Source revision not specified! Will use latest revision instead!')
        pkg_info['SVNCO'] = 'HEAD'
    subprocess.check_call(['svn', 'co', '-r', pkg_info['SVNCO']])
    return True


def src_hg_fetch(url):
    raise NotImplementedError()
    return True


def src_bzr_fetch(url):
    raise NotImplementedError()
    return True


def src_bk_fetch(url):
    raise NotImplementedError()
    return True


'''
External downloaders
'''


def test_downloaders():
    use_progs = []
    if test_progs(['aria2c', '-h']):
        use_progs.append('aria')
    if test_progs(['wget', '-h']):
        use_progs.append('wget')
    if test_progs(['curl', '-h']):
        use_progs.append('curl')
    if test_progs(['axel', '-h']):
        use_progs.append('axel')
    return use_progs


def axel_get(url, threads=4, output=None):
    axel_cmd = ['axel', '-n', threads, '-a', url]
    if output is not None:
        axel_cmd.insert(4, '-o')
        axel_cmd.insert(5, output)
    try:
        subprocess.check_call(axel_cmd)
    except KeyboardInterrupt:
        raise KeyboardInterrupt()
    except:
        raise AssertionError('Failed to fetch source with Axel!')
    return


def curl_get(url, output=None):
    curl_cmd = ['curl', url]  # , '-k'
    if output is not None:
        curl_cmd.insert(2, '-o')
        curl_cmd.insert(3, output)
    else:
        curl_cmd.insert(2, '-O')
    try:
        subprocess.check_call(curl_cmd)
    except KeyboardInterrupt:
        raise KeyboardInterrupt()
    except:
        raise AssertionError('Failed to fetch source with cURL!')
    return


def wget_get(url, output):
    wget_cmd = ['wget', '-c', url]  # ,'--no-check-certificate'
    if output is not None:
        wget_cmd.insert(2, '-O')
        wget_cmd.insert(3, output)
    try:
        subprocess.check_call(wget_cmd)
    except KeyboardInterrupt:
        raise KeyboardInterrupt()
    except:
        raise AssertionError('Failed to fetch source with Wget!')
    return


def aria_get(url, threads=3, output=None):
    if os.path.exists(output) and not os.path.exists(output+'.aria2'):
        return
    aria_cmd = ['aria2c', '--max-connection-per-server={}'.format(threads), url, '--auto-file-renaming=false']  # ,'--check-certificate=false'
    if output is not None:
        aria_cmd.insert(2, '-d')
        aria_cmd.insert(3, dump_loc)
        aria_cmd.insert(4, '-o')
        aria_cmd.insert(5, output.split('/')[-1])
    try:
        subprocess.check_call(aria_cmd)
    except KeyboardInterrupt:
        raise KeyboardInterrupt()
    except:
        raise AssertionError('Failed to fetch source with Aria2!')
    return
