# -*- coding: utf-8 -*-
from setuptools import setup

setup(
    name='adb-utils',
    version='1.0.7',
    author='hakaboom',
    author_email='1534225986@qq.com',
    license='Apache License 2.0',
    description='This is a secondary package of adb',
    url='https://github.com/hakaboom/base_image',
    packages=['adbutils'],
    install_requires=["baseImage==1.0.6"],
)