# -*- coding: utf-8 -*-

import sys
import os
import pandas as pd
from . import wingdbstub


class VisumAttributes:
    """
    Store the contents of the attribute.xlsx-file in parquet-files
    purpose is to automatically create the VisumTable classes
    """
    @classmethod
    def from_excel(cls,
                   folder: str,
                   visum_version: int = 2023,
                   language='Eng',
                   excel_file: str = None):

        self = super().__new__(cls)
        if not excel_file:
            visum_attribute_file = 'attribute.xlsx'
            visum_folder = rf'C:\Program Files\PTV Vision\PTV Visum {visum_version}\Doc\{language}'
            excel_file = os.path.join(visum_folder, visum_attribute_file)
        self.tables = pd.read_excel(excel_file,
                                    sheet_name='Tables',
                                    usecols=range(7))\
            .set_index('Name')
        self.attributes = pd.read_excel(excel_file,
                                        sheet_name='Attributes',
                                        usecols=range(24))\
            .set_index(['Object', 'AttributeID'])
        self.relations = pd.read_excel(excel_file,
                                       sheet_name='Relation',
                                       usecols=range(7))\
            .set_index(['TabFrom', 'TabTo', 'RoleName'])

        executable_backup = sys.executable
        visum_version = os.path.split(executable_backup)[-1]
        sys.executable = sys.executable.replace(visum_version, "Python\\pythonw.exe")
        try:
            self.tables.to_parquet(os.path.join(folder, 'tables.parquet'), engine="pyarrow")
            self.attributes.to_parquet(os.path.join(folder, 'attributes.parquet'), engine="pyarrow")
            self.relations.to_parquet(os.path.join(folder, 'relations.parquet'), engine="pyarrow")
        finally:
            sys.executable = executable_backup

        self.set_index()
        return self

    @classmethod
    def from_parquet(cls, folder):
        self = super().__new__(cls)
        executable_backup = sys.executable
        visum_version = os.path.split(executable_backup)[-1]
        sys.executable = sys.executable.replace(visum_version, "Python\\pythonw.exe")
        try:
            self.tables = pd.read_parquet(os.path.join(folder, 'tables.parquet'), engine="pyarrow")
            self.attributes = pd.read_parquet(os.path.join(folder, 'attributes.parquet'), engine="pyarrow")
            self.relations = pd.read_parquet(os.path.join(folder, 'relations.parquet'), engine="pyarrow")
        finally:
            sys.executable = executable_backup
        self.set_index()
        return self

    def set_index(self):
        """set the shortGerman-name as index"""
        attrs = self.attributes.reset_index()
        attrs['col'] = attrs['AttributeShort(ENG)'].str.upper()
        is_empty = attrs['col'].isna()
        attrs.loc[is_empty, 'col'] = attrs.loc[is_empty,
                                               'AttributeID'].str.upper()
        attrs = attrs.set_index(['Object', 'col'])
        self.attributes = attrs
