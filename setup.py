from setuptools import Extension, setup


class get_pybind_include:
    """Helper class to determine the pybind11 include path
    The purpose of this class is to postpone importing pybind11
    until it is actually installed, so that the ``get_include()``
    method can be invoked."""

    def __str__(self):
        try:
            import pybind11
        except ImportError:
            return ""
        return pybind11.get_include()


setup(
    ext_modules=[
        Extension(
            "acbs.miniapt_query",
            sorted(["src/miniapt-query.cc"]),
            include_dirs=[str(get_pybind_include())],
            extra_link_args=["-lapt-pkg"],
            language="c++",
            optional=True,
        )
    ],
    scripts=["acbs-build"]
)
