from setuptools import setup, find_packages

setup(
    name='bndyda',
    version='2.6.2',
    description='Make Dyda pipeline as BerryNet service.',
    url='https://github.com/DT42/BerryNet/bndyda',
    author='DT42',
    author_email='marvin42@dt42.io',
    license='DT42',
    packages=find_packages(exclude=['tests']),
    python_requires='>=3.4',
    # install_requires=[
    # ],
    # package_data={
    # },
    entry_points={
        'console_scripts': [
            'dlbox-output-processor=bndyda.output_processor:main',
            'dlbox-pipeline=bndyda.bnpipeline:main',
            'dlbox-pipeline-restarter=bndyda.pipeline_restarter:main',
            'dlbox-warmup=bndyda.warmup:main'
        ]
    },
    test_suite='tests'
)
