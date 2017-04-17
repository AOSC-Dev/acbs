ACBS
====

**ACBS is still under heavy development, but is currently deployed for packaging
for AOSC OS.**

ACBS (AutoBuild CI Build System) is a re-implementation of the original ABBS
(AutoBuild Build Service) in Python. The re-implementation aims to improve
the horrible reliability and agility of its predecessor, adding with:

- Multi-tree support (a "forest", so to speak).
- Checksum verification support.
- Cache cleaning and management support.
- Logging support.
- Proper dependency calculation (automatic build sequences, useful for
  bootstrapped bases).

Extra blings are also included:

- Build timing utilities.
- More detailed error messages.

Dependencies
------------

Mandatory:
  - Python 3 (>= 3.3): Running the program itself.
  - GNU File (libmagic): File type detection.
  - Util-Linux: File checksum verification.
  - LibArchive (bsdtar): Archive handling.
  - GNU Wget or Aria2: Source downloading.
  - [Autobuild3](https://github.com/AOSC-Dev/autobuild3): Package building.

Optional:
  - psutils: Build timing, disk space detection, device health (temperature).
  - libmagic: Python module to detect file type.
  - libarchive-c: Python module to handle archives.
  - pycrypto: Python module to verify file checksums.
  - ptyprocess, pexpect: Build logging.

Deployment
----------

ACBS could be deployed in any appropriate directories, and is invoked by calling
`acbs-build.py` (you may create a symlink for your convenience). You would need
to create a configuration file before using ACBS.

ACBS uses an INI-like configuration controlling trees to be used, the
configuration file should be stored in `/etc/acbs/forest.conf`.

A bare-minimal example is shown below:

```
[default]
location = /usr/lib/acbs/repo
```

If you are feeling smart, variable substitutions are also acceptable:

```
[vars]
base = /mnt

[default]
location = ${vars:base}/aosc-os-abbs
```

By default, ACBS builds packages from the tree defined in the `[default]` block.

Usage
-----

```
usage: acbs-build.py [-h] [-v] [-d] [-t ACBS_TREE] [-c] [-s]
                     [packages [packages ...]]

ACBS - AOSC CI Build System
Version: (README)
A small alternative system to port abbs to CI environment to prevent from
irregular bash failures

positional arguments:
  packages              Packages to be built

optional arguments:
  -h, --help            show this help message and exit
  -v, --version         Show the version and exit
  -d, --debug           Increase verbosity to ease debugging process
  -t ACBS_TREE, --tree ACBS_TREE
                        Specify which abbs-tree to use
  -c, --clear           Clear build directory
  -s, --system-log      Pass logs to system log collector
```
