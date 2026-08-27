import json
import logging
import os
import shutil
import subprocess
from collections.abc import Callable
from urllib.error import HTTPError
from urllib.parse import urlparse
from urllib.request import urlopen

from acbs.base import ACBSPackageInfo, ACBSSourceInfo
from acbs.crypto import check_hash_hashlib, hash_url
from acbs.utils import guess_extension_name

logger = logging.getLogger(__name__)

fetcher_signature = Callable[[ACBSSourceInfo,
                              str, str], ACBSSourceInfo | None]
processor_signature = Callable[[ACBSPackageInfo, int, str], None]
pair_signature = tuple[fetcher_signature, processor_signature]
generate_mode = False


def fetch_source(info: list[ACBSSourceInfo], source_location: str, package_name: str) -> ACBSSourceInfo | None:
    logger.info('Fetching required source files...')
    for count, i in enumerate(info, 1):
        logger.info(f'Fetching source ({count}/{len(info)})...')
        # in generate mode, we need to fetch all the sources
        if not i.enabled and not generate_mode:
            logger.info(f'Source {count} skipped.')
        # special handling for PyPI type
        url = i.url if i.type != "pypi" else f"pypi://{i.url}/{i.revision}"
        url_hash = hash_url(url)
        fetch_source_inner(i, source_location, url_hash)
    return None


def fetch_source_inner(info: ACBSSourceInfo, source_location: str, package_name: str) -> ACBSSourceInfo | None:
    type_ = info.type
    retry = 0
    fetcher: pair_signature | None = handlers.get(type_.upper())
    if not fetcher or not callable(fetcher[0]):
        raise NotImplementedError(f'Unsupported source type: {type_}')
    while retry < 5:
        retry += 1
        try:
            return fetcher[0](info, source_location, package_name)
        except Exception:
            logger.exception("build error")
            logger.warning(f'Retrying ({retry}/5)...')
            continue
    raise RuntimeError(
        'Unable to fetch source files, failed 5 times in a row.')


def process_source(info: ACBSPackageInfo, source_name: str) -> None:
    for idx, source_uri in enumerate(info.source_uri):
        type_ = source_uri.type
        fetcher: pair_signature | None = handlers.get(type_.upper())
        if not fetcher or not callable(fetcher[1]):
            raise NotImplementedError(
                f'Unsupported source type: {type_}')
        fetcher[1](info, idx, source_name)


# Fetchers implementations
def tarball_fetch(info: ACBSSourceInfo, source_location: str, name: str) -> ACBSSourceInfo | None:
    if source_location:
        filename = hash_url(info.url)
        if not info.chksum[1] and not generate_mode:
            raise ValueError('No checksum found. Please specify the checksum!')
        full_path = os.path.join(source_location, filename)
        wget_download(info.url, full_path)
        info.source_location = full_path
        return info


def wget_download(url: str, full_path: str):
    flag_path = full_path + ".dl"
    url_info = urlparse(url)
    if os.path.exists(full_path) and not os.path.exists(flag_path):
        return
    if url_info.hostname == 'sourceforge.net':
        if url_info.path.endswith('/download'):
            url = url_info._replace(query='failedmirror=cyfuture.dl.sourceforge.net').geturl()
        else:
            url = url_info._replace(query='failedmirror=cyfuture.dl.sourceforge.net', path=url_info.path+'/download').geturl()
    try:
        # `touch ${flag_path}`, some servers may not support Range, so this is to ensure
        # if the download has finished successfully, we don't overwrite the downloaded file
        with open(flag_path, 'wb') as f:
            f.write(b'')
        subprocess.check_call(
            ['wget', '--connect-timeout=20', '-c', url, '-O', full_path])
        os.unlink(flag_path)  # delete the flag
    except (OSError, subprocess.CalledProcessError) as exc:
        raise RuntimeError('Failed to fetch source with Wget!') from exc

def tarball_processor_innner(package: ACBSPackageInfo, index: int, source_name: str, decompress=True) -> None:
    info = package.source_uri[index]
    if not info.source_location:
        raise ValueError('Where is the source file?')
    logger.info('Computing %s checksum for %s...', info.chksum, info.source_location)
    check_hash_hashlib(info.chksum, info.source_location)

    server_filename = os.path.basename(info.url)
    extension = guess_extension_name(server_filename)
    if len(extension) == 0:
        # also guess from downloaded file name
        # pypi (maybe other fetcher) use tarball processor, but has no file extension in info.url
        extension = guess_extension_name(info.source_location)

    # this name is used in the build directory (will be seen by the build scripts)
    # the name will be, e.g. 'acbs-0.1.0.tar.gz'
    facade_name = info.source_name or '{name}-{version}{index}{extension}'.format(
        name=source_name, version=package.version, extension=extension,
        index=('' if index == 0 else f'-{index}'))
    os.symlink(info.source_location, os.path.join(
        package.build_location, facade_name))
    if not decompress:
        return
    # decompress
    logger.info(f'Extracting {facade_name}...')
    subprocess.check_call(['bsdtar', '--no-xattrs', '-xf', facade_name],
                          cwd=package.build_location)
    return


def tarball_processor(package: ACBSPackageInfo, index: int, source_name: str) -> None:
    return tarball_processor_innner(package, index, source_name)


def pypi_fetch(info: ACBSSourceInfo, source_location: str, name: str) -> ACBSSourceInfo | None:
    # https://warehouse.pypa.io/api-reference/json.html#release
    api = f"https://pypi.org/pypi/{info.url}/{info.revision}/json"
    logger.info("Querying PyPI API endpoint for source URL...")
    try:
        with urlopen(api, timeout=20) as response:
            result = json.load(response)
    except HTTPError as exc:
        logger.error(f"Got response {exc.code}")
        raise RuntimeError("Failed to query PyPI API endpoint") from exc

    actual_url = ""
    for r in result["urls"]:
        if r["packagetype"] == "sdist":
            actual_url = r["url"]
            break
    if actual_url == "":
        raise RuntimeError("Can't find source URL")
    logger.info(f"Source URL is {actual_url}")

    ext = guess_extension_name(actual_url)
    full_path = os.path.join(source_location, name + ext)
    wget_download(actual_url, full_path)
    info.source_location = full_path
    return info


def blob_processor(package: ACBSPackageInfo, index: int, source_name: str) -> None:
    return tarball_processor_innner(package, index, source_name, False)


def git_fetch(info: ACBSSourceInfo, source_location: str, name: str) -> ACBSSourceInfo | None:
    full_path = os.path.join(source_location, name)
    env = {'GIT_TERMINAL_PROMPT': '0'}
    for predefined in ['http_proxy', 'https_proxy']:
        if predefined in os.environ:
            env[predefined] = os.environ[predefined]
    if not os.path.exists(full_path):
        subprocess.check_call(['git', 'clone', '--bare', '--filter=blob:none', info.url, full_path], env=env)
    else:
        logger.info('Updating repository...')
        # --prune: prune remote-tracking branches no longer on remote
        # --tags: fetch all tags and associated objects
        # --force: force overwrite of local reference
        subprocess.check_call(
            ['git', 'fetch', 'origin', '+refs/heads/*:refs/heads/*', '--prune', '--tags', '--force'], cwd=full_path, env=env)
    info.source_location = full_path
    return info


def git_processor(package: ACBSPackageInfo, index: int, source_name: str) -> None:
    info = package.source_uri[index]
    if not info.revision:
        raise ValueError(
            'Please specify a specific git commit for this package. (GITCO not defined)')
    if not info.source_location:
        raise ValueError('Where is the git repository?')
    checkout_location = os.path.join(package.build_location, info.source_name or source_name)
    os.mkdir(checkout_location)
    logger.info(f'Checking out git repository at {info.revision}')
    subprocess.check_call(
        ['git', '--git-dir', info.source_location, '--work-tree', checkout_location,
         'checkout', '-f', info.revision or ''])
    if info.submodule > 0:
        logger.info('Fetching submodules (if any)...')
        params = [
                'git', '--git-dir', info.source_location, '--work-tree', checkout_location,
                'submodule', 'update', '--init', '--filter=blob:none'
            ]
        if info.submodule == 2:
            params.append('--recursive')
        subprocess.check_call(params, cwd=checkout_location)
    if info.copy_repo:
        logger.info('Copying git folder...')
        shutil.copytree(info.source_location, os.path.join(checkout_location, '.git'))
        with open(os.path.join(checkout_location, '.git', 'config'), 'r+') as f:
            content = f.read()
            content = content.replace('bare = true', 'bare = false')
            f.seek(0)
            f.write(content)
            f.truncate()
        return
    with open(os.path.join(package.build_location, '.acbs-script'), 'wt') as f:
        f.write(
            f'ACBS_SRC=\'{info.source_location}\';acbs_copy_git(){{ abinfo \'Copying git folder...\'; cp -ar "${{ACBS_SRC}}" .git/; sed -i \'s|bare = true|bare = false|\' \'.git/config\'; }}')


def svn_fetch(info: ACBSSourceInfo, source_location: str, name: str) -> ACBSSourceInfo | None:
    full_path = os.path.join(source_location, name)
    if not info.revision:
        raise ValueError(
            'Please specify a svn revision for this package. (SVNCO not defined)')
    logger.info(
        f'Checking out subversion repository at r{info.revision}')
    if not os.path.exists(full_path):
        subprocess.check_call(
            ['svn', 'co', '--force', '-r', info.revision, info.url, full_path])
    else:
        subprocess.check_call(
            ['svn', 'up', '--force', '-r', info.revision], cwd=full_path)
    info.source_location = full_path
    return info


def svn_processor(package: ACBSPackageInfo, index: int, source_name: str) -> None:
    info = package.source_uri[index]
    if not info.source_location:
        raise ValueError('Where is the subversion repository?')
    checkout_location = os.path.join(package.build_location, info.source_name or source_name)
    logger.info('Copying subversion repository...')
    shutil.copytree(info.source_location, checkout_location)


def hg_fetch(info: ACBSSourceInfo, source_location: str, name: str) -> ACBSSourceInfo | None:
    full_path = os.path.join(source_location, name)
    if not os.path.exists(full_path):
        subprocess.check_call(['hg', 'clone', '-U', info.url, full_path])
    else:
        logger.info('Updating repository...')
        subprocess.check_call(['hg', 'pull'], cwd=full_path)
    info.source_location = full_path
    return info


def hg_processor(package: ACBSPackageInfo, index: int, source_name: str) -> None:
    info = package.source_uri[index]
    if not info.revision:
        raise ValueError(
            'Please specify a specific hg commit for this package. (HGCO not defined)')
    if not info.source_location:
        raise ValueError('Where is the hg repository?')
    checkout_location = os.path.join(package.build_location, info.source_name or source_name)
    logger.info('Copying hg repository...')
    shutil.copytree(info.source_location, checkout_location)
    logger.info(f'Checking out hg repository at {info.revision}')
    subprocess.check_call(
        ['hg', 'update', '-C', '-r', info.revision, '-R', checkout_location])
    if info.copy_repo:
        logger.info('Copying hg repository ...')
        shutil.copytree(info.source_location, os.path.join(checkout_location, '.hg'))


def dummy_fetch(info: ACBSSourceInfo, source_location: str, name: str) -> ACBSSourceInfo | None:
    if source_location:
        logger.info('Not fetching any source as requested')
        return info
    return None


def dummy_processor(package: ACBSPackageInfo, index: int, source_name: str) -> None:
    return None


def bzr_fetch(info: ACBSSourceInfo, source_location: str, name: str) -> ACBSSourceInfo | None:
    full_path = os.path.join(source_location, name)
    if not os.path.exists(full_path):
        subprocess.check_call(['bzr', 'branch', '--no-tree', info.url, full_path])
    else:
        logger.info('Updating repository...')
        subprocess.check_call(['bzr', 'pull'], cwd=full_path)
    info.source_location = full_path
    return info


def bzr_processor(package: ACBSPackageInfo, index: int, source_name: str) -> None:
    info = package.source_uri[index]
    if not info.revision:
        raise ValueError(
            'Please specify a specific bzr revision for this package. (BZRCO not defined)')
    if not info.source_location:
        raise ValueError('Where is the bzr repository?')
    checkout_location = os.path.join(package.build_location, info.source_name or source_name)
    logger.info('Copying bzr repository...')
    shutil.copytree(info.source_location, checkout_location)
    logger.info(f'Checking out bzr repository at {info.revision}')
    subprocess.check_call(
        ['bzr', 'co', '-r', info.revision], cwd=checkout_location)


def fossil_fetch(info: ACBSSourceInfo, source_location: str, name: str) -> ACBSSourceInfo | None:
    full_path = os.path.join(source_location, name + '.fossil')
    if not os.path.exists(full_path):
        subprocess.check_call(['fossil', 'clone', info.url, full_path])
    else:
        logger.info('Updating repository...')
        subprocess.check_call(['fossil', 'pull', '-R', full_path])
    info.source_location = full_path
    return info


def fossil_processor(package: ACBSPackageInfo, index: int, source_name: str) -> None:
    info = package.source_uri[index]
    if not info.revision:
        raise ValueError(
            'Please specify a specific fossil commit for this package. (not defined)')
    if not info.source_location:
        raise ValueError('Where is the fossil repository?')
    checkout_location = os.path.join(package.build_location, info.source_name or source_name)
    os.mkdir(checkout_location)
    logger.info('Opening up the fossil repository...')
    subprocess.check_call(
        ['fossil', 'open', info.source_location], cwd=checkout_location)
    logger.info(f'Checking out fossil repository at {info.revision}')
    subprocess.check_call(['fossil', 'update', info.revision], cwd=checkout_location)


handlers: dict[str, pair_signature] = {
    'GIT': (git_fetch, git_processor),
    'SVN': (svn_fetch, svn_processor),
    'BZR': (bzr_fetch, bzr_processor),
    'HG': (hg_fetch, hg_processor),
    'FOSSIL': (fossil_fetch, fossil_processor),
    'TARBALL': (tarball_fetch, tarball_processor),
    'FILE': (tarball_fetch, blob_processor),
    'PYPI': (pypi_fetch, tarball_processor),
    'NONE': (dummy_fetch, dummy_processor),
}
