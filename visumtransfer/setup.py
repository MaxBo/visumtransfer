# -*- coding: utf-8 -*-
"""
Created on Fri Jun 10 20:33:08 2016

@author: MaxBohnet
"""
import numpy as np

from setuptools import setup, find_packages


setup(
    name="visumtransfer",
    version="0.1",
    description="Write Visum-Transfer Files",

    packages=find_packages('src', exclude=['ez_setup']),
    namespace_packages=['visumtransfer'],

    package_dir={'': 'src'},
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
    ],
)
