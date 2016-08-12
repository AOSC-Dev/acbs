#!/bin/env python
import os
import logging

'''
ACBS Search
'''


class acbs_find(object):

    def __init__(self, target):
        self.target = target
        self.path = '.'

    def acbs_pkg_match(self):
        if self.target.split('/')[0] == 'groups' and os.path.isfile(self.target):
            with open(self.target, 'rt') as cmd_list:
                pkg_list_str = cmd_list.read()
            pkg_list = pkg_list_str.split('\n')
            group_pkg = []
            for pkg in pkg_list:
                match_res = self.acbs_pkg_match_core(target=pkg)
                if match_res is not None:
                    group_pkg.append(match_res)
            return group_pkg
        else:
            return self.acbs_pkg_match_core()

    def acbs_pkg_match_core(self, target=None):
        if target is None:
            target = self.target
        if os.path.isdir(target):
            return target
        target_slug = target.split('/')
        if len(target_slug) > 1:
            target = target_slug[1]
        outer_dirlist = os.listdir('.')
        inner_dirlist = []
        global cur_dir
        cur_dir = ''
        for i in outer_dirlist:
            if os.path.isdir(i):
                cur_dir = i
                inner_dirlist = os.listdir(i)
                for j in inner_dirlist:
                    if os.path.isdir(i + '/' + j):
                        if j == target and self.acbs_verify_pkg('%s/%s' % (cur_dir, j)):
                            return '{}/{}'.format(cur_dir, j)
        return None

    def acbs_verify_pkg(self, path):
        if os.path.exists(os.path.join(path, 'spec')):
            # and os.path.exists(os.path.join(path,'autobuild/defines')):
            return True
        else:
            logging.error(
                'Candidate package\033[93m {} \033[0mdoesn\'t seem to be valid!'.format(path))
            return False
