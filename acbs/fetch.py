import subprocess
import logging
import os
import shutil
import subprocess
from typing import Callable, Optional, Tuple, Dict

from acbs.base import ACBSPackageInfo, ACBSSourceInfo
from acbs.crypto import check_hash_hashlib
from acbs.utils import guess_extension_name

fetcher_signature = Callable[[ACBSSourceInfo,
                              str, str], Optional[ACBSSourceInfo]]
processor_signature = Callable[[ACBSPackageInfo, str], None]
pair_signature = Tuple[fetcher_signature, processor_signature]


def fetch_source(info: ACBSSourceInfo, source_location: str, package_name: str) -> Optional[ACBSSourceInfo]:
    logging.info('Fetching required source files...')
    type_ = info.type
    fetcher: Optional[pair_signature] = handlers.get(type_.upper())
    if not fetcher or not callable(fetcher[0]):
        raise NotImplementedError('Unsupported source type: {}'.format(type_))
    return fetcher[0](info, source_location, package_name)


def process_source(info: ACBSPackageInfo, source_name: str) -> None:
    type_ = info.source_uri.type
    fetcher: Optional[pair_signature] = handlers.get(type_.upper())
    if not fetcher or not callable(fetcher[1]):
        raise NotImplementedError('Unsupported source type: {}'.format(type_))
    return fetcher[1](info, source_name)


# Fetchers implementations
def tarball_fetch(info: ACBSSourceInfo, source_location: str, name: str) -> Optional[ACBSSourceInfo]:
    if source_location:
        filename = ''
        if info.chksum[1]:
            filename = info.chksum[1]
        else:
            raise ValueError('No checksum found. Please specify the checksum!')
        full_path = os.path.join(source_location, filename)
        flag_path = os.path.join(source_location, '{}.dl'.format(filename))
        if os.path.exists(full_path) and not os.path.exists(flag_path):
            info.source_location = full_path
            return info
        try:
            # `touch ${flag_path}`, some servers may not support Range, so this is to ensure
            # if the download has finished successfully, we don't overwrite the downloaded file
            with open(flag_path, 'wb') as f:
                f.write(b'')
            subprocess.check_call(
                ['wget', '-c', info.url, '-O', full_path])
            info.source_location = full_path
            os.unlink(flag_path)  # delete the flag
            return info
        except Exception:
            raise AssertionError('Failed to fetch source with Wget!')
        return None
    return None


def tarball_processor(package: ACBSPackageInfo, source_name: str) -> None:
    info = package.source_uri
    if not info.source_location:
        raise ValueError('Where is the source file?')
    check_hash_hashlib(info.chksum, info.source_location)
    server_filename = os.path.basename(info.url)
    extension = guess_extension_name(server_filename)
    # this name is used in the build directory (will be seen by the build scripts)
    # the name will be, e.g. 'acbs-0.1.0.tar.gz'
    facade_name = '{name}-{version}{extension}'.format(
        name=source_name, version=package.source_uri.version, extension=extension)
    os.symlink(info.source_location, os.path.join(
        package.build_location, facade_name))
    # decompress
    logging.info('Extracting {}...'.format(facade_name))
    subprocess.check_call(['bsdtar', '-xf', facade_name],
                          cwd=package.build_location)
    return


def git_fetch(info: ACBSSourceInfo, source_location: str, name: str) -> Optional[ACBSSourceInfo]:
    full_path = os.path.join(source_location, name)
    if not os.path.exists(full_path):
        subprocess.check_call(['git', 'clone', '--bare', info.url, full_path])
    else:
        logging.info('Updating repository...')
        subprocess.check_call(['git', 'fetch', '--all'], cwd=full_path)
    info.source_location = full_path
    return info


def git_processor(package: ACBSPackageInfo, source_name: str) -> None:
    info = package.source_uri
    if not info.revision:
        raise ValueError(
            'Please specify a specific git commit for this package. (GITCO not defined)')
    if not info.source_location:
        raise ValueError('Where is the git repository?')
    checkout_location = os.path.join(package.build_location, source_name)
    os.mkdir(checkout_location)
    logging.info('Checking out git repository at {}'.format(info.revision))
    subprocess.check_call(
        ['git', '--git-dir', info.source_location, '--work-tree', checkout_location,
         'checkout', '-f', info.revision or ''])
    logging.info('Fetching submodules (if any)...')
    subprocess.check_call(
        ['git', '--git-dir', info.source_location, '--work-tree', checkout_location, 'submodule', 'update', '--init', '--recursive'], cwd=checkout_location)
    with open(os.path.join(package.build_location, '.acbs-script'), 'wt') as f:
        f.write(
            'ACBS_SRC=\'%s\';acbs_copy_git(){ cp -ar "${ACBS_SRC}" .git/; sed -i \'s|bare = true|bare = false|\' \'.git/config\'; }' % (info.source_location))
    return None


def svn_fetch(info: ACBSSourceInfo, source_location: str, name: str) -> Optional[ACBSSourceInfo]:
    full_path = os.path.join(source_location, name)
    if not info.revision:
        raise ValueError(
            'Please specify a svn revision for this package. (SVNCO not defined)')
    logging.info(
        'Checking out subversion repository at r{}'.format(info.revision))
    if not os.path.exists(full_path):
        subprocess.check_call(
            ['svn', 'co', '--force', '-r', info.revision, info.url, full_path])
    else:
        subprocess.check_call(
            ['svn', 'up', '--force', '-r', info.revision], cwd=full_path)
    info.source_location = full_path
    return info


def svn_processor(package: ACBSPackageInfo, source_name: str) -> None:
    info = package.source_uri
    if not info.source_location:
        raise ValueError('Where is the subversion repository?')
    checkout_location = os.path.join(package.build_location, source_name)
    logging.info('Copying subversion repository...')
    shutil.copytree(info.source_location, checkout_location)
    return


def hg_fetch(info: ACBSSourceInfo, source_location: str, name: str) -> Optional[ACBSSourceInfo]:
    full_path = os.path.join(source_location, name)
    if not os.path.exists(full_path):
        subprocess.check_call(['hg', 'clone', '-U', info.url, full_path])
    else:
        logging.info('Updating repository...')
        subprocess.check_call(['hg', 'pull'], cwd=full_path)
    info.source_location = full_path
    return info


def hg_processor(package: ACBSPackageInfo, source_name: str) -> None:
    info = package.source_uri
    if not info.revision:
        raise ValueError(
            'Please specify a specific hg commit for this package. (HGCO not defined)')
    if not info.source_location:
        raise ValueError('Where is the hg repository?')
    checkout_location = os.path.join(package.build_location, source_name)
    logging.info('Copying hg repository...')
    shutil.copytree(info.source_location, checkout_location)
    logging.info('Checking out hg repository at {}'.format(info.revision))
    subprocess.check_call(
        ['hg', 'update', '-C', '-r', info.revision, '-R', checkout_location])
    return None


def dummy_fetch(info: ACBSSourceInfo, source_location: str, name: str) -> Optional[ACBSSourceInfo]:
    if source_location:
        logging.info('Not fetching any source as requested')
        return info
    return None


def dummy_processor(package: ACBSPackageInfo, source_name: str) -> None:
    return None


handlers: Dict[str, pair_signature] = {
    'GIT': (git_fetch, git_processor),
    'SVN': (svn_fetch, svn_processor),
    # 'BZR': (None,),
    'HG': (hg_fetch, hg_processor),
    'TARBALL': (tarball_fetch, tarball_processor),
    'NONE': (dummy_fetch, dummy_processor),
}
