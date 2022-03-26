# -*- coding: utf-8 -*-
from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()


setup(
    name='adb-utils',
    version='1.0.16',
    author='hakaboom',
    author_email='1534225986@qq.com',
    license='Apache License 2.0',
    description='This is a secondary package of adb',
    long_description=long_description,
    long_description_content_type="text/markdown",
    url='https://github.com/hakaboom/adb-utils',
    packages=find_packages(),
    include_package_data=True,
    install_requires=["loguru>=0.5.3",
                      "baseImage==1.1.1"],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.8',
)
