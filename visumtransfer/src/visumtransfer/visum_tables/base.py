# -*- coding: utf-8 -*-

import numpy as np
import pandas as pd
from visumtransfer.visum_table import VisumTable



class Network(VisumTable):
    name = 'Network'
    code = 'NETWORK'
    _mode = ''
    _cols = ''
    _defaults = {0: 0}

    @property
    def pkey(self):
        return [0]

    def validate_df(self, df: pd.DataFrame):
        """Validate the DataFrame, may be defined differently in the subclass"""
        if len(self.df) > 1:
            raise ValueError(f'{self.__class__} may have only one row')


class UserDefinedGroup(VisumTable):
    name = 'Userdefined Groups'
    code = 'USERDEFINEDGROUP'

    _cols = 'NAME;DESCRIPTION'


class UserDefinedAttribute(VisumTable):
    name = 'Userdefined Attributes'
    code = 'USERDEFINEDATTRIBUTE'

    _cols = ('OBJID;ATTID;CODE;NAME;VALUETYPE;MINVALUE;MAXVALUE;'
    'DEFAULTVALUE;DEFAULTSTRINGVALUE;COMMENT;MAXSTRINGLENGTH;NUMDECPLACES;'
    'DATASOURCETYPE;FORMULA;CROSSSECTIONLOGIC;USERDEFINEDGROUPNAME')

    _pkey = 'OBJID;ATTID'

    _defaults = {'VALUETYPE': 'Double',
                 'CROSSSECTIONLOGIC': 'SUM',
                 'NUMDECPLACES': 3,
                 'MAXSTRINGLENGTH': 255,
                 'MINVALUE': 'MIN',
                 'MAXVALUE': 'MAX',
                 }

    def add_formula_attribute(self,
                             objid: str,
                             name: str,
                             formula: str,
                             attid: str=None,
                             code: str=None,
                             userdefinedgroupname: str=None,
                             **kwargs):
        """
        add formula-attribute

        Parameters
        ----------
        objid : str
            the network type like NETWORK, ACTIVITY etc.
        name : str
            the name of the attribute, will be used as code and attid, too,
            if they are not explicitely specified
        formula : str
            the formula
        attid : str, optional
            the attid. If None, the code, and if the code is None, name will be taken
        code : str, optional
            the code. If None, the name will be taken
        """
        attid = attid or code or name
        code = code or name
        self.add(objid=objid,
                 datasourcetype='FORMULA',
                 name=name,
                 attid=attid,
                 code=code,
                 formula=formula,
                 userdefinedgroupname=userdefinedgroupname,
                 **kwargs)

    def add_data_attribute(self,
                            objid: str,
                            name: str,
                            attid: str=None,
                            code: str=None,
                            userdefinedgroupname: str=None,
                            **kwargs):
        """
        add Data-Attribute

        Parameters
        ----------
        objid : str
            the network type like NETWORK, ACTIVITY etc.
        name : str
            the name of the attribute, will be used as code and attid, too,
            if they are not explicitely specified
        attid : str, optional
            the attid. If None, the code, and if the code is None, name will be taken
        code : str, optional
            the code. If None, the name will be taken
        """
        attid = attid or code or name
        code = code or name
        row = self.Row(objid=objid,
                       datasourcetype='DATEN',
                       name=name,
                       attid=attid,
                       code=code,
                       userdefinedgroupname=userdefinedgroupname,
                       **kwargs)
        self.add_row(row)



class TSys(VisumTable):
    name = 'Transport Systems'
    code = 'TSYS'

    _cols = 'CODE;TYPE'


class Mainzone(VisumTable):
    name = 'Mainzones'
    code = 'MAINZONE'
    _cols = 'NO;XCOORD;YCOORD'


class Zone(VisumTable):
    name = 'Zones'
    code = 'ZONE'
    _cols = 'NO'

    def read_pgr(self, fn):
        r = np.recfromtxt(open(fn, mode='rb').readlines(), delimiter=',',
                          names=True, filling_values=0)
        names = r.dtype.names[2:]
        attrs = [f'NumPersons({pg})' for pg in names]
        self._cols = ';'.join(['NO'] + attrs)

        values = r[['vz_id']+list(names)]
        self.add_rows(values.tolist())
        self._mode = '*'

    def read_strukturdaten(self, fn):
        r = np.recfromtxt(open(fn, mode='rb').readlines(), delimiter=',',
                          names=True, filling_values=0)
        names = r.dtype.names[2:]
        attrs = [f'ValStructuralProp({sg.lstrip("ValStructuralProp")})'
                 if sg.startswith('ValStructuralProp')
                 else sg
                 for sg in names]
        self._cols = ';'.join(['NO'] + list(attrs))

        values = r[['vz_id']+list(names)]
        self.add_rows(values.tolist())
        self._mode = '*'
