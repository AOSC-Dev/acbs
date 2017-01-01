#!/bin/env python3
'''
ACBS - AOSC CI Build System
A small alternative system to port abbs to CI environment to prevent
from irregular bash failures
'''
import os
import sys
import shutil
import argparse
from acbs.mainflow import acbs_build_core


def main():
    tmp_loc = '/var/cache/acbs/build/'
    acbs_version = '20170101'
    parser = argparse.ArgumentParser(description=help_msg(acbs_version
                                                          ), formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('-v', '--version',
                        help='Show the version and exit', action="version", version='ACBS version {}'.format(acbs_version))
    parser.add_argument(
        '-d', '--debug', help='Increase verbosity to ease debugging process', action="store_true")
    parser.add_argument('-t', '--tree', nargs=1, dest='acbs_tree',
                        help='Specify which abbs-tree to use')
    parser.add_argument('packages', nargs='*', help='Packages to be built')
    parser.add_argument('-c', '--clear', help='Clear build directory',
                        action='store_true', dest='clear_dir')
    parser.add_argument('-s', '--system-log', help='Pass logs to system log collector', action='store_true', dest='syslog')
    args = parser.parse_args()
    if args.clear_dir:
        clear_tmp(tmp_dir=tmp_loc)
    if len(args.packages) > 0:
        acbs_core_args = {'pkgs_name': args.packages,
                          'debug_mode': args.debug, 'version': acbs_version}
        if args.syslog:
            acbs_core_args['syslog'] = True
        if args.acbs_tree:
            acbs_core_args['tree'] = args.acbs_tree[0]
            acbs_instance = acbs_build_core(**acbs_core_args)
        else:
            acbs_instance = acbs_build_core(**acbs_core_args)
        acbs_instance.build()
    # HACK: Workaround a bug in ArgumentParser
    if len(sys.argv) < 2:
        sys.argv.insert(1, '-h')
        main()
    sys.exit(0)


def clear_tmp(tmp_dir):
    from time import sleep

    def show_progress():
        try:
            print(hide_cursor, end='')
            while not complete_status:
                for bar in ['-', '\\', '|', '/']:
                    print('\r[%s%%] Clearing cache...%s' %
                          (int((sub_dirs_deleted / sub_dirs_count) * 100), bar), end='')
                    sys.stdout.flush()
                    sleep(0.1)
            print('\r[100%%] Clearing cache...done! %s\n' %
                  (show_cursor), end='')
        except Exception as ex:
            print(show_cursor, end='')
            raise ex
    import threading
    hide_cursor = '\033[?25l'
    show_cursor = '\033[?25h'
    sub_dirs = os.listdir(tmp_dir)
    sub_dirs_count = len(sub_dirs)
    if not sub_dirs_count:
        print('Build directory clean, no need to clear...')
        print(show_cursor, end='')
        return
    sub_dirs_deleted = 0
    complete_status = False
    indicator = threading.Thread(target=show_progress)
    indicator.start()
    for dirs in sub_dirs:
        shutil.rmtree(os.path.join(tmp_dir, dirs))
        sub_dirs_deleted += 1
    complete_status = True
    return


def help_msg(acbs_version):
    help_msg = '''ACBS - AOSC CI Build System\nVersion: {}\nA small alternative system to port abbs to CI environment to prevent from irregular bash failures'''.format(acbs_version)
    return help_msg

if __name__ == '__main__':
    main()
