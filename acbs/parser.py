import os
import re
import logging
import tempfile
import subprocess
import re
# import logging
import configparser

from acbs import utils

# In AB3, we allow for a version-spec suffix on a DEP when processing.
re_version_spec = re.compile('(?:[<>=]=.*|_)$')

def pkgs_nover(pkgs):
    # Until something proves otherwise we will strip it off for now...
    return [re_version_spec.sub('', p) for p in pkgs]

class Parser(object):

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
        script = 'ARCH={}\n{}{}'.format(utils.get_arch_name(), spec_cont, utils.gen_laundry_list([
            'VER', 'REL', 'SUBDIR', 'SRCTBL', 'GITSRC', 'GITCO', 'GITBRCH',
            'SVNSRC', 'SVNCO', 'HGSRC', 'BZRSRC', 'BZRCO', 'DUMMYSRC', 'CHKSUM'
        ]))
        try:
            acbs_config.read_file(conf_file)
        except Exception as ex:
            raise ValueError(
                'Malformed spec file found! Couldn\'t continue!') from ex
        # Assume it's UTF-8 since we have no clue of the real world on how it
        # works ... (just don't want to use chardet)
        spec_fp = io.StringIO('[wrap]\n' + spec_out.decode('utf-8'))
        config = configparser.RawConfigParser()
        config.read_file(spec_fp)
        config_dict = {}
        for i in config['wrap']:
            config_dict[i.upper()] = config['wrap'][i]
        config_dict['NAME'] = self.pkg_name
        self.abd_config = config_dict
        self.parser_validate(config_dict)
        self.shared_data.version = [config_dict['VER'], config_dict['REL']]
        if config_dict['CHKSUM']:
            self.shared_data.chksums = [tuple(i.split('::')) for i in config_dict[
                'CHKSUM'].split(' ')]
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
                'Failed to load autobuild defines file! Does the file exist?') from ex
        script = "ARCH={}\n{}{}".format(
            utils.get_arch_name(), abd_cont,
            utils.gen_laundry_list(['PKGNAME', 'PKGDEP', 'BUILDDEP']))
        try:
            # Better to be replaced by subprocess.Popen
            abd_out = subprocess.check_output(script, shell=True)
        except Exception as ex:
            raise Exception(
                'Malformed Autobuild defines file found! Couldn\'t continue!') from ex
        abd_fp = io.StringIO('[wrap]\n' + abd_out.decode('utf-8'))
        abd_config = configparser.RawConfigParser()
        abd_config.read_file(abd_fp)
        abd_config_dict = {}
        for i in abd_config['wrap']:
            abd_config_dict[i.upper()] = abd_config['wrap'][i]
        self.shared_data.build_deps = pkgs_nover(abd_config_dict['BUILDDEP'].split())
        self.shared_data.run_deps = pkgs_nover(abd_config_dict['PKGDEP'].split())
        self.shared_data.opt_deps = []  # abd_config_dict['PKGREC'] <RfF>
        self.shared_data.buffer['ab3_def'] = abd_config_dict
        return self.shared_data

    def parser_validate(self, in_dict):
        # just a simple naive validate for now
        if in_dict['NAME'] == '' or in_dict['VER'] == '':
            raise ValueError('Package name or version not valid!!!')
        if utils.check_empty(utils.LOGIC_OR, in_dict, ['SRCTBL', 'GITSRC', 'SVNSRC', 'HGSRC', 'BZRSRC']) is True:
            if in_dict['DUMMYSRC'] not in ['true', '1']:
                raise ValueError('No source specified!')

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

    def parse_acbs_conf(self, tree_name):
        self.forest_file = os.path.join(self.conf_loc, 'forest.conf')
        acbs_config = configparser.RawConfigParser()
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
                                                                               utils.list2str(acbs_config.sections()))
            raise ValueError(err_message) from ex
        try:
            tree_loc = tree_loc_dict['location']
        except KeyError as ex:
            raise KeyError(
                'Malformed configuration file: missing `location` keyword') from ex
        return tree_loc

    def write_acbs_conf(self):
        acbs_conf_writer = configparser.RawConfigParser()
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

class ACBSVCSInfo(object):

    def __init__(self, proto='', url='', branch='', rev=''):
        self.proto = proto
        self.url = url
        self.branch = branch
        self.rev = rev
        self.buffer = {}

    def clear(self):
        self.__init__()

    def update(self, other):
        self.proto = other.proto or self.proto
        self.branch = other.branch or self.branch
        self.rev = other.rev or self.rev
        self.url = other.url or self.url
        self.buffer = utils.merge_dicts(self.buffer, other.buffer)

    def __eq__(self, other):
        # Ignore buffer
        return (self.proto == other.proto)  \
            and (self.url == other.url) and \
            (self.rev == other.rev) and (self.branch == other.branch)


class ACBSPackageInfo(object):

    def __init__(self, directory, subdir='autobuild', name=None, rootpath=None):
        self.directory = directory
        self.pkg_name = directory.rsplit('/', 1)[-1]
        self.subdir = subdir
        self.rootpath = rootpath or os.path.abspath('.')
        self.version = None
        self.chksums = []  # format: [tuples]=>Just don't want to import od :-)
        self.abbs_data = {}
        self.ab3_def = {}
        self.issubpkg = (subdir != 'autobuild')

        self.run_deps = []
        self.build_deps = []
        self.opt_deps = []

        self.src_name = None
        self.src_path = None
        self.temp_dir = None

    def __repr__(self):
        return "ACBSPackageInfo(%r, %r)" % (self.directory, self.subdir)

    def ab_dir(self):
        return os.path.abspath(os.path.join(
            self.rootpath, self.directory, self.subdir))

    def update(self, other):
        self.src_name = other.src_name.strip() or self.src_name
        self.src_path = other.src_path or self.src_path
        self.version = other.version or self.version
        self.opt_deps = utils.uniq(self.opt_deps + other.opt_deps)
        self.build_deps = utils.uniq(self.build_deps + other.build_deps)
        self.run_deps = utils.uniq(self.run_deps + other.run_deps)
        self.chksums = other.chksums or self.chksums
        self.buffer = utils.merge_dicts(self.buffer, other.buffer)

    def parse_abbs_spec(self):
        try:
            with open(self.spec_file_loc + '/spec', 'rt') as spec_file:
                spec_cont = spec_file.read()
        except OSError as e:
            raise OSError(
                'Failed to load spec file! Do you have read permission?') from e
        script = 'ARCH={}\n{}'.format(utils.get_arch_name(), spec_cont)
        try:
            # Better to be replaced by subprocess.Popen
            spec_vars = eval_bashvar_ext(script)
        except Exception as ex:
            raise ValueError(
                'Malformed spec file found! Couldn\'t continue!') from ex
        # Assume it's UTF-8 since we have no clue of the real world on how it
        # works ... (just don't want to use chardet)
        spec_validate(spec_vars)
        self.version = (spec_vars['VER'], spec_vars.get('REL', ''))
        if spec_vars.get('CHKSUM'):
            self.chksums = [tuple(i.split('::'))
                for i in spec_vars['CHKSUM'].split(' ')]
        self.abbs_data = spec_vars

    def parse_ab3_defines(self):
        defines_file = os.path.join(
            self.rootpath, self.directory, self.subdir, 'defines')
        try:
            with open(defines_file, 'rt') as abd_file:
                abd_cont = abd_file.read()
        except OSError as ex:
            raise OSError(
                'Failed to load autobuild defines file! Does the file exist?') from ex
        script = "ARCH={}\n{}{}".format(utils.get_arch_name(), abd_cont)
        try:
            # Better to be replaced by subprocess.Popen
            abd_vars = eval_bashvar_ext(script)
        except Exception as ex:
            raise Exception(
                'Malformed Autobuild defines file found! Couldn\'t continue!') from ex
        self.pkg_name = abd_vars['PKGNAME']
        self.build_deps = abd_vars.get('BUILDDEP', '').split()
        self.run_deps = abd_vars.get('PKGDEP', '').split()
        self.opt_deps = []  # abd_vars.get('PKGREC', '') <RfF>
        self.ab3_def = abd_vars

    def write_ab3_defines(self, rootpath):  # config_dict, spec_file_loc):
        write_ab = {'PKGVER': self.abbs_data['VER'],
                    'PKGREL': self.abbs_data.get('REL', '')}
        filename = os.path.join(rootpath, self.subdir, 'defines')
        try:
            with open(filename, 'at') as fp:
                fp.write('\n')
                for k, v in write_ab.items():
                    fp.write('%s=\"%s\"\n' % (k, v))
        except IOError as ex:
            raise Exception(
                'Failed to update information in \033[36m{}\033[0m'.format(
                filename)) from ex

class ACBSPackageGroup(ACBSPackageInfo):

    re_subpackage = re.compile(r'^\d+-')

    def __repr__(self):
        return "ACBSPackageGroup(%r, %r)" % (self.directory, self.subdir)

    def package(self, subdir):
        cls = ACBSPackageInfo(self.directory, subdir, rootpath=self.rootpath)
        cls.version = self.version
        cls.chksums = self.chksums
        cls.abbs_data = self.abbs_data.copy()
        cls.ab3_def = self.ab3_def.copy()
        cls.run_deps = self.run_deps
        cls.build_deps = self.build_deps
        cls.opt_deps = self.opt_deps
        cls.src_name = self.src_name
        cls.src_path = self.src_path
        cls.temp_dir = self.temp_dir
        cls.parse_ab3_defines()
        return cls

    def subpackages(self):
        sub_dirs = []
        path = os.path.join(self.rootpath, self.directory)
        for _, sub_dirs, _ in os.walk(path):
            break
        if len(sub_dirs) > 1:
            sub_pkgs = []
            for subdir in sub_dirs:
                if self.re_subpackage.match(subdir):
                    sub_pkgs.append(self.package(subdir))
                else:
                    logging.warning('Unknown folder: %s in tree' % subdir)
            return sub_pkgs
        elif len(sub_dirs) == 1:
            subdir = sub_dirs[0]
            if subdir != 'autobuild':
                raise AssertionError('The only directory is not "autobuild".')
            return [self.package(subdir)]
        else:
            return []
