from collections import ChainMap
import inspect
import os
from pathlib import Path
import shlex
import subprocess
import sys

from setuptools import Extension, find_packages, setup
from setuptools.command.build_ext import build_ext
from setuptools.command.develop import develop
from setuptools.command.install_lib import install_lib
import versioneer


class get_pybind_include(object):
    """Helper class to determine the pybind11 include path.

    The purpose of this class is to postpone importing pybind11 until it is
    actually installed, so that the ``get_include()`` method can be invoked.
    """

    def __init__(self, user=False):
        self.user = user

    def __str__(self):
        import pybind11
        return pybind11.get_include(self.user)


def get_pkg_config(info, lib):
    return shlex.split(subprocess.check_output(["pkg-config", info, lib],
                                               universal_newlines=True))


EXTENSION = Extension(
    "mplcairo._mplcairo",
    ["src/_mplcairo.cpp", "src/_util.cpp", "src/_pattern_cache.cpp"],
    depends=
        ["setup.py", "src/_mplcairo.h", "src/_util.h", "src/_pattern_cache.h"],
    language=
        "c++",
    include_dirs=
        [get_pybind_include(), get_pybind_include(user=True)],
    extra_compile_args=
        {"linux":
            ["-std=c++17", "-fvisibility=hidden"]
            + (get_pkg_config("--cflags", "py3cairo")
               if not os.environ.get("MANYLINUX") else
               ["-static-libgcc", "-static-libstdc++",
                "-I/usr/include/cairo",
                "-I/usr/include/freetype2",
                "-I/usr/include/pycairo"]),
         "darwin":
            ["-std=c++17", "-fvisibility=hidden", "-mmacosx-version-min=10.7"],
         "win32":
            ["/std:c++17", "/EHsc", "/D_USE_MATH_DEFINES",
             # Windows conda paths.
             "-I{}".format(Path(sys.prefix, "Library/include")),
             "-I{}".format(Path(sys.prefix, "Library/include/cairo")),
             "-I{}".format(Path(sys.prefix, "include/pycairo"))]}
        [sys.platform],
    extra_link_args=
        {"linux":
            ([]
             if not os.environ.get("MANYLINUX") else
             ["-static-libgcc", "-static-libstdc++"]),
         "darwin":
            # Min version needs to be repeated to avoid a warning.
            ["-mmacosx-version-min=10.9"],
         "win32":
            []}
        [sys.platform]
)


class build_ext(build_ext):
    def build_extensions(self):
        # Workaround https://bugs.llvm.org/show_bug.cgi?id=33222 (clang +
        # libstdc++ + std::variant = compilation error).
        if (subprocess.check_output([self.compiler.compiler[0], "--version"],
                                    universal_newlines=True)
                .startswith("clang")):
            EXTENSION.extra_compile_args += ["-stdlib=libc++"]
            # Explicitly linking to libc++ is required to avoid picking up the
            # system C++ library (libstdc++ or an outdated libc++).
            EXTENSION.extra_link_args += ["-lc++"]
        super().build_extensions()


def _pth_hook():
    if os.environ.get("MPLCAIRO"):
        from importlib.machinery import PathFinder
        class PyplotMetaPathFinder(PathFinder):
            def find_spec(self, fullname, path=None, target=None):
                spec = super().find_spec(fullname, path, target)
                if fullname == "matplotlib.backends.backend_agg":
                    def exec_module(module):
                        type(spec.loader).exec_module(spec.loader, module)
                        # The pth file does not get properly uninstalled from
                        # a develop install.  See pypa/pip#4176.
                        try:
                            import mplcairo.base
                        except ImportError:
                            return
                        module.FigureCanvasAgg = \
                            mplcairo.base.FigureCanvasCairo
                        module.RendererAgg = \
                            mplcairo.base.GraphicsContextRendererCairo
                    spec.loader.exec_module = exec_module
                    sys.meta_path.remove(self)
                return spec
        sys.meta_path.insert(0, PyplotMetaPathFinder())


class _pth_command_mixin:
    def run(self):
        super().run()
        with Path(self.install_dir, "mplcairo.pth").open("w") as file:
            file.write("import os; exec({!r}); _pth_hook()"
                       .format(inspect.getsource(_pth_hook)))

    def get_outputs(self):
        return (super().get_outputs()
                + [str(Path(self.install_dir, "mplcairo.pth"))])


setup(
    name="mplcairo",
    description="A (new) cairo backend for Matplotlib.",
    long_description=open("README.rst", encoding="utf-8").read(),
    version=versioneer.get_version(),
    cmdclass=ChainMap(
        versioneer.get_cmdclass(),
        {"build_ext": build_ext,
         "develop": type("", (_pth_command_mixin, develop), {}),
         "install_lib": type("", (_pth_command_mixin, install_lib), {})}),
    author="Antony Lee",
    url="https://github.com/anntzer/mplcairo",
    license="MIT",
    classifiers=[
        "Development Status :: 4 - Beta",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6"
    ],
    packages=find_packages("lib"),
    package_dir={"": "lib"},
    ext_modules=[EXTENSION],
    python_requires=">=3.4",
    install_requires=["pybind11>=2.2", "pycairo>=1.12.0"],
)
