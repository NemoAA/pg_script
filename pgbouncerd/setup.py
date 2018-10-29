import sys
from setuptools import setup

data_files = None

if sys.version_info < (2, 6):
    raise SystemExit('ERROR: pgbouncerd need at least python 2.6 to work.')

setup(
    name='pgbouncerd',
    version='0.1',
    author='Nemo deng',
    author_email='dbyzaa@163.com',
    scripts=['pgbouncerd'],
    url='https://github.com/NemoAA/pg_script/tree/master/pgbouncerd',
    license='LICENSE.txt',
    description='Command line tool for PgBouncer server daemon.',
    install_requires=[
        "psutil >= 0.4.1",
        "setproctitle >= 1.1.10",
    ],
    data_files=data_files,
)
