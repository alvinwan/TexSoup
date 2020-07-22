import sys
from setuptools import setup
from setuptools.command.test import test as test_command

tests_require = ['pytest', 'pytest-cov==2.5.1',
                 'coverage==4.4', 'coveralls==1.1']
install_requires = []


with open("README.md", "r") as fh:
    long_description = fh.read()


class PyTest(test_command):
    user_options = [('pytest-args=', 'a', "Arguments to pass to py.test")]

    def __init__(self, dist, **kw):
        super().__init__(dist, **kw)
        self.pytest_args = []

    def initialize_options(self):
        test_command.initialize_options(self)

    def finalize_options(self):
        test_command.finalize_options(self)

    def run_tests(self):
        # import here, cause outside the eggs aren't loaded
        import pytest
        errno = pytest.main(self.pytest_args)
        sys.exit(errno)


VERSION = '0.3.0'

setup(
    name="TexSoup",
    version=VERSION,
    author="Alvin Wan",
    author_email='hi@alvinwan.com',
    description=("parses valid LaTeX and provides variety of Beautiful-Soup-"
                 "esque methods and Pythonic idioms for iterating over and "
                 "searching the parse tree"),
    long_description=long_description,
    long_description_content_type="text/markdown",
    license="BSD",
    url="https://github.com/alvinwan/TexSoup",
    packages=['TexSoup'],
    cmdclass={'test': PyTest},
    tests_require=tests_require,
    install_requires=install_requires,
    download_url='https://github.com/alvinwan/TexSoup/archive/%s.zip' % VERSION,
    classifiers=[
        "Topic :: Utilities",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Topic :: Software Development :: Libraries",
    ],
)
