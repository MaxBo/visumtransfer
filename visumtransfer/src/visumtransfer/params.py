import json
import tables
import pandas as pd
import openpyxl
from numpy import recarray
from typing import List


class Params:
    modes: tables.Table
    gg: recarray
    gd: recarray
    g_cali: recarray
    g_pkw: recarray
    activities: recarray
    activity_parking: recarray
    activitypairs: recarray
    activitypair_time_series: recarray
    time_series: recarray
    trip_chain_rates: recarray
    validation_activities: recarray
    validation_activities_hauptweg: recarray
    validation_modes: recarray
    """"""
    attr2tablename = dict(
        gg='groups.groups_generation',
        gd='groups.groups_dest_mode',
        g_cali='groups.groups_calibration',
        g_pkw='groups.groups_pkwverf',
        activities='activities.activities',
        activity_parking='activities.activity_parking',
        activitypairs='activities.activitypairs',
        activitypair_time_series='activities.activitypair_time_series',
        time_series='activities.time_series',
        trip_chain_rates='activities.trip_chain_rates',
        validation_activities='activities.validation_activities',
        validation_activities_hauptweg='activities.hauptweg',
        validation_modes='groups.validation_mode',
        modes='modes.modes', )

    def __init__(self, h5: tables.File):
        for k, v in self.attr2tablename.items():
            node_name = '/{}'.format(v.replace('.', '/'))
            node = h5.get_node(node_name)
            setattr(self, k, node[:])

    @property
    def mode_set(self):
        modes = self.modes['code']
        return ','.join(modes)

    def save2excel(self, excel_fp: str, keys: List = None):
        """Save parameters in different excel sheets"""
        with pd.ExcelWriter(excel_fp, engine='openpyxl') as excel:
            try:
                excel.book = openpyxl.load_workbook(excel_fp)
            except FileNotFoundError:
                pass
            for k, v in self.attr2tablename.items():
                if keys is None or k in keys:
                    recarray = getattr(self, k)
                    df = pd.DataFrame(recarray)
                    for col_name in df.columns:
                        col = df[col_name]
                        if col.dtype.char == 'O' and isinstance(col[0], bytes):
                            df[col_name] = col.str.decode('cp1252')

                    sheet_name = v.replace('.', '_')[:30]
                    try:
                        old_sheet = excel.book.get_sheet_by_name(sheet_name)
                        excel.book.remove_sheet(old_sheet)
                    except KeyError:
                        pass
                    df.to_excel(excel, sheet_name=sheet_name)

    @classmethod
    def from_excel(cls, excel_fp: str) -> 'Params':
        """read params-file from excel"""
        self = cls.__new__(cls)
        self.dataframes = {}
        with pd.ExcelFile(excel_fp) as excel:

            for k, v in cls.attr2tablename.items():
                sheet_name = v.replace('.', '_')[:30]
                df = pd.read_excel(excel, sheet_name,
                                   keep_default_na=False)
                for colname in df.columns:
                    try:
                        converted = pd.to_numeric(df[colname])
                        df.loc[:, colname] = converted
                    except ValueError:
                        pass

                self.dataframes[k] = df
                recarray = df.to_records()
                setattr(self, k, recarray)
        return self

    def __repr__(self):
        tbls = json.dumps(self.attr2tablename, indent=2)
        #return tbls
        return f'Params-object with the following tables: {tbls}'


def read_params(param_file):
    with tables.open_file(param_file, 'a') as h5:
        params = Params(h5)
    return params
