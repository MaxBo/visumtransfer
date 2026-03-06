# -*- coding: utf-8 -*-

import pandas as pd
from visumtransfer.visum_table import VisumTable


class Mode(VisumTable):
    name = 'Modes'
    code = 'MODE'
    _cols = 'CODE;NAME;TSYSSET;INTERCHANGEABLE'


class Demandmodel(VisumTable):
    name = 'Demandmodels'
    code = 'DEMANDMODEL'
    _cols = 'CODE;NAME;TYPE;MODESET'


class StructuralProp(VisumTable):
    name = 'Structural properties'
    code = 'STRUCTURALPROP'
    _cols = 'CODE;NAME;DEMANDMODELCODE'

    def create_tables(self,
                      activities: pd.DataFrame,
                      model: str,
                      suffix=''):
        rows = []
        for idx, a in activities.iterrows():
            # Heimataktivität hat keine Strukturgröße
            if not a['potential']:
                continue
            row = self.Row(demandmodelcode=model)
            row.code = a['potential'] + suffix
            row.name = a['name']
            rows.append(row)
        self.add_rows(rows)


class StructuralPropValues(VisumTable):
    name = 'Structural property values'
    code = 'STRUCTURALPROPVALUES'
    _cols = 'ZONENO;STRUCTURALPROPCODE;VALUE'
    _longformat = True
    _mode = ''


class PersonGroupPerZone(VisumTable):
    name = 'Person group per zone'
    code = 'PERSONGROUPPERZONE'
    _cols = 'ZONENO;PERSONGROUPCODE;NUMPERSONS'
    _longformat = True
    _mode = ''


class DemandDescription(VisumTable):
    name = 'Demand Description'
    code = 'DEMANDDESCRIPTION'
    _cols = 'DSEGCODE;DEMANDTIMESERIESNO;MATRIXREF'
    _defaults = {'DEMANDTIMESERIESNO': 1}
