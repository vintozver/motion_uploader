# -*- coding: utf-8 -*-

from setuptools import setup

setup(
    name='motion_uploader',
    version='1.0',
    description='\
motion daemon uploader. \
Uploads the pictures to Microsoft OneDrive as soon as they arrive at the storage.\
',
    author='Vitaly Greck',
    author_email='vintozver@ya.ru',
    url='https://www.python.org/sigs/distutils-sig/',
    packages=['motion_uploader'],
    install_requires=[],
    entry_points={
        'console_scripts': [
            'motion_uploader_service=motion_uploader.service:main',
            'motion_uploader_auth=motion_uploader.auth:main',
        ],
    },
)