import subprocess

from setuptools import setup
from setuptools import find_packages


with open("README.md", "r") as f:
    long_description = f.read()


setup(
    name='berrynet',
    version='v3.10.1',
    description='Deep learning gateway on Raspberry Pi and other edge devices.',
    long_description=long_description,
    long_description_content_type="text/markdown",
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
        'paho-mqtt',
        'PyOpenGL',
        'PyOpenGL-accelerate',
    ],
    # Without TF: pip3 install berrynet
    # TF CPU mode: pip3 install berrynet[tf]
    # TF GPU mode: pip3 install berrynet[tf_gpu]
    # TF GPU mode and Wheel-version OpenCV: pip3 install berrynet[tf_gpu, opencv]
    extra_require={
        'tf': ['tensorflow>=1.2.1'],
        'tf_gpu': ['tensorflow-gpu>=1.2.1'],
        'opencv': ['opencv-python']
    },
    python_requires='>=3',  # recognized by pip >= 9.0.0
    # The "Including Data Files" session
    # https://setuptools.readthedocs.io/en/latest/setuptools.html
    #
    # Warning: package_data only looks for module's top level
    #package_data={
    #},
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
    entry_points={
        'console_scripts': [
            'bn_camera=berrynet.client.camera:main',
            'bn_dashboard=berrynet.client.fbdashboard:main',
            'bn_data_collector=berrynet.client.data_collector:main',
            'bn_gmail=berrynet.client.gmail:main',
            'bn_telegram=berrynet.client.telegram_bot:main',
            'bn_tflite=berrynet.service.tflite_service:main',
            'bn_openvino=berrynet.service.openvino_service:main',
            'bn_darknet=berrynet.service.darknet_service:main',
            'bn_pipeline=bndyda.bnpipeline:main',
        ]
    },
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
