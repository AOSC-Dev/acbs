import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="acbs",
    version="0.1.20200620",
    author="liushuyu",
    author_email="liushuyu@aosc.io",
    description="AOSC CI Building System",
    license="GNU Lesser General Public License v2 (LGPLv2)",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/AOSC-Dev/acbs",
    packages=setuptools.find_packages(),
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
    scripts=["acbs-build"]
)
