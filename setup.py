# -*- coding: utf-8 -*-
from setuptools import setup, find_packages

setup(
    name='adb-utils',
    version='1.0.14',
    author='hakaboom',
    author_email='1534225986@qq.com',
    license='Apache License 2.0',
    description='This is a secondary package of adb',
    url='https://github.com/hakaboom/adb-utils',
    packages=find_packages(),
    include_package_data=True,
    install_requires=["baseImage==1.0.6"],
)
