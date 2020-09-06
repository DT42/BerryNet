from setuptools import setup, find_packages

setup(
    name='bntrainer',
    version='2.6.2',
    description='Make trainer pipeline as BerryNet service.',
    url='https://gitlab.com/DT42/marvin42/dlbox-release',
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
            'dlbox-output-processor=bntrainer.output_processor:main',
            'dlbox-pipeline=bntrainer.pipeline:main',
            'dlbox-pipeline-restarter=bntrainer.pipeline_restarter:main',
            'dlbox-warmup=bntrainer.warmup:main'
        ]
    },
    test_suite='tests'
)
