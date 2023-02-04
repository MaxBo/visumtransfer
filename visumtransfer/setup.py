# -*- coding: utf-8 -*-
"""
Created on Fri Jun 10 20:33:08 2016

@author: MaxBohnet
"""
from setuptools import setup, find_packages


setup(
    name="visumtransfer",
    description="Write Visum-Transfer Files",
    packages=find_packages('src'),
    namespace_packages=['visumtransfer'],
    package_dir={'': 'src'},
    package_data={'': ['attributes.h5'], },
    include_package_data=True,
    zip_safe=False,
    data_files=[
    ],

    extras_require=dict(
        extra=[],
        test=[]
    ),

    install_requires=[
        'pandas',
        'xarray',
        'openpyxl',
        'recordclass',
        'pytest',
    ],
)
