#!/usr/bin/env python3

"""
This allows to build the package, deploy it in PyPi and tag the source in GitHub:

> pip install -r requirements.txt
> rm -rf dist
> ./setup.py sdist
> twine upload dist/*
> git tag 0.0.1
> git push origin --tags

"""

from setuptools import find_packages, setup

with open("README.md", "r") as readme:
    README = readme.read()

setup(
    name='rediscache',
    packages=find_packages(),
    version='0.0.1',
    description='Function decorator to cache results in Redis',
    long_description=README,
    long_description_content_type='text/markdown',
    # Classifiers: https://pypi.org/classifiers/
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.8.5',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
    author='Pierre Cart-Grandjean',
    author_email='pcart-grandjean@users.noreply.github.com',
    maintainer='Amadeus IT Group',
    maintainer_email="opensource@amadeus.com",
    url='https://github.com/AmadeusITGroup/RedisCache',
    keywords=['redis', 'performance', 'cache'],
    license='MIT license',
    copyright='Copyright (c) 2020 Amadeus s.a.s.',
    install_requires=[
        'redis',
        'executiontime'
    ],
)
