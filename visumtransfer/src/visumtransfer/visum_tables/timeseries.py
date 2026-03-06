# -*- coding: utf-8 -*-

import xarray as xr
import pandas as pd
from .demand import DemandDescription
from .persongroups import PersonGroup
from visumtransfer.visum_table import VisumTable



class TimeSeriesItem(VisumTable):
    name = 'Time Series Items'
    code = 'TIMESERIESITEM'
    _cols = 'TIMESERIESNO;STARTTIME;ENDTIME;WEIGHT;MATRIXREF'
    _pkey = 'TIMESERIESNO;STARTTIME;ENDTIME'


class DemandTimeSeries(VisumTable):
    name = 'DemandTimeSeries'
    code = 'DEMANDTIMESERIES'
    _cols = 'NO;CODE;NAME;TIMESERIESNO'


class VisemTimeSeries(VisumTable):
    name = 'VISEM-TimeSeries'
    code = 'VISEMTIMESERIES'
    _cols = 'ACTIVITYPAIRCODE;PERSONGROUPCODE;TIMESERIESNO'
    _pkey = 'ACTIVITYPAIRCODE;PERSONGROUPCODE'


class TimeSeries(VisumTable):
    name = 'TimeSeries'
    code = 'TIMESERIES'
    _cols = 'NO;NAME;TYPE'
    _defaults = {'TYPE': 'Shares'}

    def create_tables(self,
                      activitypairs: pd.DataFrame,
                      time_series: pd.DataFrame,
                      ap_timeseries: pd.DataFrame,
                      timeseriesitem: TimeSeriesItem,
                      demandtimeseries: DemandTimeSeries,
                      visem_timeseries: VisemTimeSeries,
                      persongroups: PersonGroup,
                      start_idx=100,
                      ):

        rows = []
        rows_ganglinienelement = []
        rows_nachfrageganglinien = []
        rows_visem_nachfrageganglinien = []
        ap_timeseries = ap_timeseries\
            .reset_index()\
            .set_index(['index', 'activitypair'])

        for a, ap in activitypairs.iterrows():
            ap_code = ap['code']
            idx = ap['idx']
            no = idx + start_idx
            row = self.Row(no=no, name=ap_code)
            rows.append(row)

            # Nachfrageganglinie
            row_nachfrageganglinie = demandtimeseries.Row(
                no=no, code=ap_code, name=ap_code, timeseriesno=no)
            rows_nachfrageganglinien.append(row_nachfrageganglinie)

            # Ganglinie
            ap_timeserie = ap_timeseries.iloc[idx]
            for t, ts in time_series.iterrows():
                from_hour = ts['from_hour']
                to_hour = ts['to_hour']
                anteil = ap_timeserie.iloc[from_hour:to_hour].sum()
                if anteil:
                    row_ganglinienelement = timeseriesitem.Row(
                        timeseriesno=no,
                        starttime=from_hour * 3600,
                        endtime=to_hour * 3600,
                        weight=anteil)
                    rows_ganglinienelement.append(row_ganglinienelement)

            # Personengruppen
            for pg_code, pg in persongroups.df.iterrows():
                row_visem_ganglinie = visem_timeseries.Row(
                    persongroupcode=pg_code, timeseriesno=no)
                if not pg['DEMANDMODELCODE'] == 'VisemGeneration':
                    row_visem_ganglinie.activitypaircode = ap_code
                rows_visem_nachfrageganglinien.append(row_visem_ganglinie)

        self.add_rows(rows)
        timeseriesitem.add_rows(rows_ganglinienelement)
        demandtimeseries.add_rows(rows_nachfrageganglinien)
        visem_timeseries.add_rows(rows_visem_nachfrageganglinien)


class DemandSegment(VisumTable):
    name = 'DemandSegments'
    code = 'DEMANDSEGMENT'
    _cols = 'CODE;NAME;MODE'
    _defaults = {'MODE': 'L'}

    def add_ov_ganglinien(self,
                          ds_timeseries: xr.Dataset,
                          timeseries: TimeSeries,
                          timeseriesitems: TimeSeriesItem,
                          demandtimeseries: DemandTimeSeries,
                          demand_description: DemandDescription,
                          start_idx: int = 80,
                          ):
        """Add Ganglinien for OV"""
        mode = 'O'
        rows_nseg = []
        rows_ganglinie = []
        rows_ganglinienelement = []
        rows_nachfrageganglinien = []
        rows_nachfragebeschreibung = []
        gl = ds_timeseries.ganglinie
        ds_timeseries['anteile_stunde'] = gl / gl.sum('stunde')

        for hap in ds_timeseries.hap:
            hap_name = hap.lab_hap.values
            mat_code = f'Visem_OV_{hap_name}'

            nsg_code = f'OV_{hap_name}'
            nseg_name = f'OV {hap_name}'

            hap_id = hap.hap.values
            nachfr_gl_nr = gl_nr = hap_id + start_idx
            gl_name = f'OV_{hap_name}'
            rows_ganglinie.append(timeseries.Row(no=gl_nr, name=gl_name))

            row_nachfrageganglinie = demandtimeseries.Row(
                no=nachfr_gl_nr, code=gl_name, name=gl_name,
                timeseriesno=gl_nr)
            rows_nachfrageganglinien.append(row_nachfrageganglinie)

            gl_stunde = ds_timeseries.anteile_stunde.sel(hap=hap_id)

            for stunde in gl_stunde:
                # in sekunden, Intervalle von 60 sec.
                starttime = stunde.stunde * 3600
                endtime = starttime + 3600
                if stunde:
                    row_ganglinienelement = timeseriesitems.Row(
                        timeseriesno=gl_nr,
                        starttime=starttime,
                        endtime=endtime,
                        weight=stunde)
                    rows_ganglinienelement.append(row_ganglinienelement)

            matrix_descr = f'MATRIX([CODE]="{mat_code}")'
            rows_nseg.append(self.Row(code=nsg_code,
                                      name=nseg_name,
                                      mode=mode))
            rows_nachfragebeschreibung.append(demand_description.Row(
                dsegcode=nsg_code,
                demandtimeseriesno=nachfr_gl_nr,
                matrixref=matrix_descr
            ))

        self.add_rows(rows_nseg)
        timeseries.add_rows(rows_ganglinie)
        demandtimeseries.add_rows(rows_nachfrageganglinien)
        timeseriesitems.add_rows(rows_ganglinienelement)
        demand_description.add_rows(rows_nachfragebeschreibung)

