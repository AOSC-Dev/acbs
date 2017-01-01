import os
import io
import subprocess
# import logging
from configparser import RawConfigParser

from lib.acbs_utils import acbs_utils


class acbs_parser(object):

    def __init__(self, main_data=None, pkg_name=None, spec_file_loc=None, defines_file_loc=None):
        self.shared_data = ACBSPackgeInfo()
        self.abbs_spec = {}
        self.abd_config = {}
        self.spec_file_loc = spec_file_loc or ''
        self.defines_file_loc = defines_file_loc or ''
        self.pkg_name = pkg_name
        self.acbs_data = {}
        self.main_data = main_data
        self.forest_file = None
        if not self.main_data:
            self.conf_loc = '/etc/acbs/'
        else:
            self.conf_loc = main_data.conf_loc
        self.forest_file = os.path.join(self.conf_loc, 'forest.conf')

    def parse_abbs_spec(self):
        try:
            with open(self.spec_file_loc + '/spec', 'rt') as spec_file:
                spec_cont = spec_file.read()
        except OSError as e:
            raise OSError(
                'Failed to load spec file! Do you have read permission?') from e
        # Stupid but necessary laundry list of possible varibles
        script = '{}{}'.format(
            spec_cont, acbs_utils.gen_laundry_list(['VER', 'REL', 'SUBDIR',
                                                    'SRCTBL', 'GITSRC',
                                                    'GITCO', 'GITBRCH',
                                                    'SVNSRC', 'SVNCO', 'HGSRC',
                                                    'BZRSRC', 'BZRCO',
                                                    'DUMMYSRC', 'CHKSUM']))
        try:
            # Better to be replaced by subprocess.Popen
            spec_out = subprocess.check_output(script, shell=True)
        except Exception as ex:
            raise ValueError(
                'Malformed spec file found! Couldn\'t continue!') from ex
        # Assume it's UTF-8 since we have no clue of the real world on how it
        # works ... (just don't want to use chardet)
        spec_fp = io.StringIO('[wrap]\n' + spec_out.decode('utf-8'))
        config = RawConfigParser()
        config.read_file(spec_fp)
        config_dict = {}
        for i in config['wrap']:
            config_dict[i.upper()] = config['wrap'][i]
        config_dict['NAME'] = self.pkg_name
        self.abd_config = config_dict
        self.parser_validate(config_dict)
        self.shared_data.version = [config_dict['VER'], config_dict['REL']]
        if config_dict['CHKSUM']:
            self.shared_data.chksums = [tuple(i.split('::')) for i in config_dict['CHKSUM'].split(' ')]
        self.shared_data.buffer['abbs_data'] = config_dict
        return self.shared_data

    def parser_pass_through(self):  # config_dict, spec_file_loc):
        write_ab = {'PKGVER': self.abbs_spec[
            'VER'], 'PKGREL': self.abbs_spec['REL']}
        return self.write_ab3_defines(self.defines_file_loc + '/autobuild/defines', write_ab)

    def parse_ab3_defines(self, defines_file):  # , pkg_name):
        try:
            with open(defines_file, 'rt') as abd_file:
                abd_cont = abd_file.read()
        except OSError as ex:
            raise OSError(
                'Failed to load autobuild defines file! Do you have read permission?') from ex
        script = "ARCH={}\n{}{}".format(
            acbs_utils.get_arch_name(), abd_cont,
            acbs_utils.gen_laundry_list(['PKGNAME', 'PKGDEP', 'BUILDDEP']))
        try:
            # Better to be replaced by subprocess.Popen
            abd_out = subprocess.check_output(script, shell=True)
        except Exception as ex:
            raise Exception(
                'Malformed Autobuild defines file found! Couldn\'t continue!') from ex
        abd_fp = io.StringIO('[wrap]\n' + abd_out.decode('utf-8'))
        abd_config = RawConfigParser()
        abd_config.read_file(abd_fp)
        abd_config_dict = {}
        for i in abd_config['wrap']:
            abd_config_dict[i.upper()] = abd_config['wrap'][i]
        self.shared_data.build_deps = abd_config_dict['BUILDDEP'].split()
        self.shared_data.run_deps = abd_config_dict['PKGDEP'].split()
        self.shared_data.opt_deps = []  # abd_config_dict['PKGREC'] <RfF>
        self.shared_data.buffer['ab3_def'] = abd_config_dict
        return self.shared_data

    def bat_parse_ab3_defines(self, defines_files):
        onion_list = []
        for def_file in defines_files:
            abd_config_dict = self.parse_ab3_defines(def_file)
            onion_list.append(abd_config_dict)
        return onion_list

    def parser_validate(self, in_dict):
        # just a simple naive validate for now
        if in_dict['NAME'] == '' or in_dict['VER'] == '':
            raise ValueError('Package name or version not valid!!!')
        if acbs_utils.check_empty(acbs_utils.LOGIC_OR, in_dict, ['SRCTBL', 'GITSRC', 'SVNSRC', 'HGSRC', 'BZRSRC']) is True:
            if in_dict['DUMMYSRC'] not in ['true', '1']:
                raise ValueError('No source specified!')
        return

    def write_ab3_defines(self, def_file_loc, in_dict):
        str_to_write = ''
        for i in in_dict:
            str_to_write = '%s%s=\"%s\"\n' % (str_to_write, i, in_dict[i])
        try:
            fp = open(def_file_loc, 'at')
            fp.write(str_to_write)
        except IOError as ex:
            raise Exception('Failed to update information in \033[36m{}\033[0m'.format(
                def_file_loc)) from ex
        return

    def parse_acbs_conf(self, tree_name):
        import configparser
        self.forest_file = os.path.join(self.conf_loc, 'forest.conf')
        acbs_config = RawConfigParser()
        acbs_config._interpolation = configparser.ExtendedInterpolation()
        with open(self.forest_file, 'rt') as conf_file:
            try:
                acbs_config.read_file(conf_file)
            except Exception as ex:
                raise Exception('Failed to read configuration file!') from ex
        try:
            tree_loc_dict = acbs_config[tree_name]
        except KeyError as ex:
            err_message = '404 - Tree not found: {}, defined trees: {}'.format(tree_name,
                                                                               acbs_utils.list2str(acbs_config.sections()))
            raise ValueError(err_message) from ex
        try:
            tree_loc = tree_loc_dict['location']
        except KeyError as ex:
            raise KeyError(
                'Malformed configuration file: missing `location` keyword') from ex
        return tree_loc

    def write_acbs_conf(self):
        acbs_conf_writer = RawConfigParser()
        acbs_conf_writer.add_section('default')
        acbs_conf_writer.set('default', 'location', '/var/lib/acbs/repo/')
        acbs_conf_writer.add_section('acbs')
        acbs_conf_writer.set('acbs', 'location', '/var/lib/acbs/repo/')
        try:
            with open(self.forest_file, 'w') as fp:
                acbs_conf_writer.write(fp)
        except Exception as ex:
            raise Exception(
                'Unable to write initial configuration file!') from ex
        return


class ACBSPackgeInfo(object):

    def __init__(self, name='', stash='', slug='', version=[], src_url=[], src_name='', src_path=''):
        self.name = name
        self.slug = slug
        self.version = version
        self.src_url = src_url
        self.src_name = src_name
        self.src_path = src_path
        self.dump_place = stash
        self.run_deps = []
        self.build_deps = []
        self.opt_deps = []
        self.chksums = []  # format: [tuples]=>Just don't want to import od :-)
        self.buffer = {}
        # Used to store un-processed data to pass to next function

    def update(self, other):
        def uniq(seq):  # Dave Kirby
            # Order preserving
            seen = set()
            return [x for x in seq if x not in seen and not seen.add(x)]
        self.src_name = other.src_name.strip() or self.src_name
        self.src_url = other.src_url or self.src_url
        self.src_path = other.src_path or self.src_path
        self.version = other.version or self.version
        self.opt_deps = uniq(self.opt_deps + other.opt_deps)
        self.build_deps = uniq(self.build_deps + other.build_deps)
        self.run_deps = uniq(self.run_deps + other.run_deps)
        self.chksums = uniq(self.chksums + other.chksums)
        self.buffer = other.buffer or self.buffer

    def clear(self):
        self = self.__init__()
