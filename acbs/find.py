#!/bin/env python
import os
import logging

'''
ACBS Search
'''


class Finder(object):

    def __init__(self, target, search_path=None):
        self.target = target
        self.path = search_path or os.path.abspath('.')

    def acbs_pkg_match(self):
        logging.debug('Search Path: %s' % self.path)
        if self.target.startswith('groups') and os.path.isfile(os.path.join(self.path, self.target)):
            with open(os.path.join(self.path, self.target), 'rt') as cmd_list:
                pkg_list_str = cmd_list.read()
            pkg_list = pkg_list_str.splitlines()
            group_pkg = []
            for pkg in pkg_list:
                if not pkg.strip():
                    continue
                match_res = self.acbs_pkg_match_core(target=pkg)
                if match_res is not None:
                    group_pkg.append(match_res)
                else:
                    logging.warning('Package %s not found!' % pkg)
            logging.debug('Packages to be built: %s' % ', '.join(group_pkg))
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
            _, target = target_slug
        categories = ('base-', 'extra-')
        for path in os.listdir(self.path):
            secpath = os.path.join(self.path, path)
            if not (os.path.isdir(secpath) and any(path.startswith(x) for x in categories)):
                continue
            category, section = path.split('-')
            for pkgpath in os.listdir(secpath):
                if pkgpath == target and os.path.isdir(os.path.join(secpath, pkgpath)):
                    return os.path.relpath(os.path.join(secpath, pkgpath), self.path)

    @staticmethod
    def determine_pkg_type(pkg):
        sub_pkgs = set(os.listdir(pkg)) - set(['spec'])
        if len(sub_pkgs) > 1:
            sub_dict = {}
            for i in sub_pkgs:
                tmp_array = i.split('-', 1)
                try:
                    sub_dict[int(tmp_array[0])] = tmp_array[1]
                except ValueError as ex:
                    raise ValueError('Expecting numeric value, got {}'.format(
                        tmp_array[0])) from ex
            return sub_dict

    def acbs_verify_pkg(self, path, strict_mode=False):
        if os.path.exists(os.path.join(path, 'spec')):
            if strict_mode and not os.path.exists(os.path.join(path, 'autobuild/defines')):
                raise Exception('Can\'t find `defines` file!')
        else:
            raise Exception(
                'Candidate package\033[93m {} \033[0mdoesn\'t seem to be valid!'.format(path))
