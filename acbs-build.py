#!/bin/env python3
'''
ACBS - AOSC CI Build System
A small alternative system to port abbs to CI environment to prevent
from irregular bash failures
'''
import os
import sys
# import shutil
import argparse
import logging
import signal
import logging.handlers
from multiprocessing import pool
# import time
from multiprocessing.pool import ThreadPool

from lib.acbs_find import acbs_find
from lib.acbs_parser import acbs_parser
from lib.acbs_src_fetch import acbs_src_fetch
from lib.acbs_deps import acbs_deps
from lib.acbs_utils import acbs_utils
from lib.acbs_utils import acbs_log_format
from lib.acbs_start_build import acbs_start_ab
from lib.acbs_misc import acbs_misc

acbs_version = '0.0.1-alpha0'
verbose = 0


def main():
    parser = argparse.ArgumentParser(description=help_msg(
    ), formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('-v', '--version',
                        help='Show the version and exit', action="store_true")
    parser.add_argument(
        '-d', '--debug', help='Increase verbosity to ease debugging process', action="store_true")
    parser.add_argument('-t', '--tree', nargs=1, dest='acbs_tree',
                        help='Specify which abbs-tree to use')
    parser.add_argument('packages', nargs='*', help='Packages to be built')
    args = parser.parse_args()
    if args.version:
        print('ACBS version {}'.format(acbs_version))
    if len(args.packages) > 0:
        if args.acbs_tree is not None:
            init_env(args.acbs_tree)
        else:
            init_env()
        sys.exit(build_pkgs(args.packages))


def init_env(tree=['default']):
    if os.getuid() != 0:
        print('Run me as ROOT!')
        sys.exit(1)
    dump_loc = '/var/cache/acbs/tarballs/'
    tmp_loc = '/var/cache/acbs/build/'
    conf_loc = '/etc/acbs/'
    log_loc = '/var/log/acbs/'
    print("----- Welcome to ACBS - %s -----" % (acbs_version))
    try:
        for dir_loc in [dump_loc, tmp_loc, conf_loc, log_loc]:
            if not os.path.isdir(dir_loc):
                os.makedirs(dir_loc)
    except:
        raise IOError('\033[93mFailed to make work directory\033[0m!')
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    str_handler = logging.StreamHandler()
    str_handler.setLevel(logging.INFO)
    str_handler.setFormatter(acbs_log_format())
    logger.addHandler(str_handler)
    log_file_handler = logging.handlers.RotatingFileHandler(
        '/var/log/acbs/acbs-build.log', mode='a', maxBytes=5120, backupCount=10)
    log_file_handler.setLevel(logging.DEBUG)
    log_file_handler.setFormatter(logging.Formatter(
        '%(asctime)s:%(levelname)s:%(message)s'))
    logger.addHandler(log_file_handler)
    signal.signal(signal.SIGUSR1, signal_handler)
    acbs_misc().dev_utilz_warn()
    if os.path.exists('/etc/acbs/forest.conf'):
        tree_loc = acbs_parser.parse_acbs_conf(tree[0])
        if tree_loc is not None:
            os.chdir(tree_loc)
        else:
            sys.exit(1)
    else:
        if not acbs_parser.write_acbs_conf():
            sys.exit(1)
    return


def build_pkgs(pkgs):
    for pkg in pkgs:
        # print(os.path.abspath(os.curdir))
        matched_pkg = acbs_find(pkg).acbs_pkg_match()
        if isinstance(matched_pkg, list):
            logging.info('Package build list found: \033[36m%s (%s)\033[0m' %
                         (os.path.basename(pkg), len(matched_pkg)))
            return build_pkgs(matched_pkg + pkgs)
        if matched_pkg is None:
            acbs_utils.err_msg(
                'No valid candidate package found for \033[36m{}\033[0m.'.format(pkg))
            # print('[E] No valid candidate package found for {}'.format(pkg))
            return -1
        else:
            if build_ind_pkg(matched_pkg) == 0:
                continue
            else:
                return -1
    return 0


def build_ind_pkg(pkg):
    logging.info('Start building \033[36m{}\033[0m'.format(pkg))
    pkg_type_res = acbs_find.determine_pkg_type(pkg)
    if not pkg_type_res:
        acbs_utils.err_msg('Malformed package group')
        return -1
    elif pkg_type_res is True:
        pass
    else:
        return build_sub_pkgs(pkg, pkg_type_res)
    try:
        pkg_slug = os.path.basename(pkg)
    except:
        pkg_slug = pkg
    ps_obj = acbs_parser(pkg_name=pkg_slug, spec_file_loc=os.path.abspath(pkg))
    abbs_spec = ps_obj.parse_abbs_spec()
    repo_dir = os.path.abspath(pkg)
    if not abbs_spec:
        acbs_utils.err_msg()
        return -1
    abd_dict = ps_obj.parse_ab3_defines(os.path.join(pkg, 'autobuild/defines'))
    deps_result, try_build = acbs_deps().process_deps(
        abd_dict['BUILDDEP'], abd_dict['PKGDEP'], pkg_slug)
    if (not deps_result) and (not try_build):
        acbs_utils.err_msg('Failed to process dependencies!')
        return -1
    if try_build:
        if not new_build_thread(try_build):
            return 128
    src_fetcher = acbs_src_fetch(abbs_spec)
    src_dispatcher_return = src_fetcher.src_dispatcher()
    if isinstance(src_dispatcher_return, tuple):
        src_proc_result, tmp_dir_loc = src_dispatcher_return
    else:
        src_proc_result = src_dispatcher_return
    if not src_proc_result:
        acbs_utils.err_msg('Failed to fetch and process source files!')
        return 1
    repo_ab_dir = os.path.join(repo_dir, 'autobuild/')
    ab3_obj = acbs_start_ab(tmp_dir_loc, repo_ab_dir, abbs_spec)
    if not ab3_obj.timed_start_ab3():
        acbs_utils.err_msg('Autobuild process failure!')
        return 1
    return 0


def signal_handler(signal, frame):
    raise ACBSTerminate()


def new_build_thread(try_build):
    for sub_pkg in list(try_build):
        dumb_mutex = pool.threading.Lock()
        dumb_mutex.acquire()
        fake_pool = ThreadPool(processes=1)
        try:
            sub_thread = fake_pool.apply_async(
                func=slave_thread_build, args=(sub_pkg))
            if not sub_thread.get():
                raise ACBSTerminate()
            dumb_mutex.release()
            return 0
        except:
            acbs_utils.err_msg(
                'Sub-build process building \033[36m{}\033[0m \033[93mfailed!\033[0m'.format(sub_pkg))
            sys.exit()
            return 128


def slave_thread_build(pkg):
    logging.debug('New build thread started for \033[36m{}\033[0m'.format(pkg))
    return build_pkgs([pkg])


def build_sub_pkgs(pkg_base, pkgs_array):
    pkg_tuple = [(lambda x, y, z: (y, '%s/0%s-%s' % (z, x, y)) if x < 10 else (y, '%s/%s-%s' %
                                                                               (z, str(x), y)))(i, pkgs_array[i], pkg_base) for i in pkgs_array]
    pkg_names = [i[1] for i in pkgs_array]
    logging.info('Package group detected\033[36m({})\033[0m: contains: \033[36m{}\033[0m'.format(
        len(pkg_tuple), ' '.join(pkg_names)))
    ps_obj = acbs_parser()
    ps_obj.pkg_name = os.path.basename(pkg_base)
    ps_obj.spec_file_loc = os.path.abspath(pkg_base)
    abbs_spec = ps_obj.parse_abbs_spec()
    pkg_def_loc = [i[1] + '/defines' for i in pkg_tuple]
    sub_repo_dir = [i[1] for i in pkg_tuple]
    onion_list = acbs_parser().bat_parse_ab3_defines(pkg_def_loc)
    if not onion_list:
        return 1
    src_dispatcher_return = acbs_src_fetch(pkg_info=abbs_spec).src_dispatcher()
    if isinstance(src_dispatcher_return, tuple):
        src_proc_result, tmp_dir_loc = src_dispatcher_return
    else:
        src_proc_result = src_dispatcher_return
    if not src_proc_result:
        acbs_utils.err_msg('Failed to fetch and process source files!')
        return 1
    sub_count = 0
    for abd_sub_dict in onion_list:
        sub_count += 1
        logging.info('[\033[36m{}/{}\033[0m] Building sub package \033[36m{}\033[0m'.format(sub_count,
                                                                                            len(onion_list), abd_sub_dict['PKGNAME']))
        pkg_slug = abd_sub_dict['PKGNAME']
        deps_result, try_build = acbs_deps().process_deps(
            abd_sub_dict['BUILDDEP'], abd_sub_dict['PKGDEP'], pkg_slug)
        if (not deps_result) and (not try_build):
            acbs_utils.err_msg('Failed to process dependencies!')
            return -1
        if try_build:
            if new_build_thread(try_build) != 0:
                return 128
        ab3_obj = acbs_start_ab(tmp_dir_loc, sub_repo_dir[
            sub_count - 1], abbs_spec, rm_abdir=True)
        if not ab3_obj.timed_start_ab3():
            acbs_utils.err_msg('Autobuild process failure on {}!'.format(
                abd_sub_dict['PKGNAME']))
            return 1
    return 0


def help_msg():
    help_msg = 'ACBS - AOSC CI Build System\nVersion: {}\nA small alternative system to port \
abbs to CI environment to prevent from irregular bash failures'.format(acbs_version)
    return help_msg


class ACBSTerminate(Exception):
    pass

if __name__ == '__main__':
    main()
