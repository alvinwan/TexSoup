import sys
from setuptools import setup
from setuptools.command.test import test as TestCommand

class PyTest(TestCommand):

    user_options = [('pytest-args=', 'a', "Arguments to pass to py.test")]

    def initialize_options(self):
        TestCommand.initialize_options(self)
        self.pytest_args = []

    def finalize_options(self):
        TestCommand.finalize_options(self)

    def run_tests(self):
        # import here, cause outside the eggs aren't loaded
        import pytest
        errno = pytest.main(self.pytest_args)
        sys.exit(errno)

VERSION = '0.0.1'

setup(
    name = "TexSoup",
    version = VERSION,
    author = "Alvin Wan",
    author_email = 'hi@alvinwan.com',
    description = ("parses valid LaTeX and provides variety of Beautiful-Soup-esque methods and Pythonic idioms for iterating over and searching the parse tree"),
    license = "BSD",
    url = "https://github.com/alvinwan/TexSoup",
    packages = ['TexSoup'],
    cmdclass = {'test': PyTest},
    tests_require = ['pytest'],
    install_requires = [],
    download_url = 'https://github.com/alvinwan/TexSoup/archive/%s.zip' % VERSION,
    classifiers = [
        "Topic :: Utilities",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Topic :: Software Development :: Libraries",
    ],
)
