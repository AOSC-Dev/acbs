from setuptools import setup, find_packages, Extension
from setuptools.command.build_ext import build_ext

from acbs import __version__


class get_pybind_include(object):
    """Helper class to determine the pybind11 include path
    The purpose of this class is to postpone importing pybind11
    until it is actually installed, so that the ``get_include()``
    method can be invoked. """

    def __str__(self):
        try:
            import pybind11
        except ImportError:
            return None
        return pybind11.get_include()


ext_modules = [Extension(
    'acbs.miniapt_query', sorted(['src/miniapt-query.cc']),
    include_dirs=[get_pybind_include()], extra_link_args=['-lapt-pkg'], language='c++', optional=True
)]

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name="acbs",
    version="0.1.{}".format(__version__),
    author="liushuyu",
    author_email="liushuyu@aosc.io",
    description="AOSC CI Building System",
    license="GNU Lesser General Public License v2 (LGPLv2)",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/AOSC-Dev/acbs",
    packages=find_packages(),
    install_requires=[
        "pyparsing>=2.4,<3"
    ],
    extras_require={
        "Build logging": ["pexpect"]
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Programming Language :: Python :: 3",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: GNU Lesser General Public License v2 (LGPLv2)",
        "Operating System :: POSIX :: Linux",
    ],
    python_requires='>=3.6',
    ext_modules=ext_modules,
    setup_requires=['pybind11>=2.5.0'],
    cmdclass={'build_ext': build_ext},
    scripts=["acbs-build"]
)
