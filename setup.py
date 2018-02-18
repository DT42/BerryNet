import subprocess

from setuptools import setup
from setuptools import find_packages


setup(
    name='berrynet',
    version='v2.3.0rc1',
    description='BerryNet',
    long_description=
        'TBD',
    url='https://github.com/DT42/BerryNet',
    author='DT42 Inc.',
    author_email='berrynet@dt42.io',
    license='GPLv3',
    # https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Science/Research',
        'Topic :: Scientific/Engineering :: Artificial Intelligence',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
    ],
    keywords=['wheels'],
    packages=find_packages(exclude=['tests']),
    install_requires=[
        'logzero',
        'opencv-python',
        'paho-mqtt',
        'tensorflow'
    ],
    python_requires='>=3',  # recognized by pip >= 9.0.0
    # The "Including Data Files" session
    # https://setuptools.readthedocs.io/en/latest/setuptools.html
    #
    # Warning: package_data only looks for module's top level
    package_data={
    },
    #data_files=[
    #    ('docs', ['docs/cheatsheet.txt', 'docs/references.txt']),
    #],
    #scripts=[
    #    'bin/purescript.sh'
    #],
    # The "Automatic Script Creation" session
    # https://setuptools.readthedocs.io/en/latest/setuptools.html
    #
    # http://python-packaging.readthedocs.io/en/latest/command-line-scripts.html
    #entry_points={
    #    'console_scripts': ['hellowheels-cli=hellowheels.command_line:main']
    #},
    #ext_modules=[
    #    Extension(
    #        'hellowheels.lib.clib',
    #        [
    #            'hellowheels/lib/clib.c',
    #            'hellowheels/lib/ext.c'
    #        ]
    #    )
    #],
    #cmdclass={
    #    'install': CustomInstallCommand
    #},
    test_suite='tests'
)
