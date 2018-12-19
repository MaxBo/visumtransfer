# -*- coding: utf-8 -*-


from collections import OrderedDict, defaultdict
from typing import Dict, List, Iterable
from copy import copy
import warnings
import os
import io
import tables
import numpy as np
import datetime
from recordclass import recordclass
import xarray as xr
import pandas as pd
import openpyxl
from visumtransfer.visum_table import VisumTable, VisumTables

folder = r'E:\GGR\1643 Oberhausen Mobilitätskonzept\60 Modell\68 Personengruppen\681 Nachfragemodell'
folder2 = r'E:\GGR\1643 Oberhausen Mobilitätskonzept\60 Modell\65 ModellOB\OB_Modell_1118\Oberhausen\SharedData'
modifications = r'E:\GGR\1643 Oberhausen Mobilitätskonzept\60 Modell\65 ModellOB\OB_Modell_1118\Oberhausen\Modifications'

param_file = os.path.join(folder, 'tdm_params.h5')
param_excel_fp = os.path.join(folder, 'tdm_params.xlsx')
file_pgr = os.path.join(folder, 'personengruppen.csv')
file_sgr = os.path.join(folder, 'strukturgroessen.csv')
file_aufteilung_arbeitswege = os.path.join(folder2, 'Factors_Commuters.csv')


class Params(object):
    """"""
    attr2tablename = dict(
    gg = 'groups.groups_generation',
    gd = 'groups.groups_dest_mode',
    g_cali = 'groups.groups_calibration',
    g_pkw = 'groups.groups_pkwverf',
    activities = 'activities.activities',
    activity_parking = 'activities.activity_parking',
    activitypairs = 'activities.activitypairs',
    activitypair_time_series = \
        'activities.activitypair_time_series',
    time_series = 'activities.time_series',
    trip_chain_rates = 'activities.trip_chain_rates',
    validation_activities = 'activities.validation_activities',
    validation_modes = 'groups.validation_mode',
    modes = 'modes.modes', )

    @property
    def mode_set(self):
        modes = self.modes['code']
        return ','.join(modes)

    @classmethod
    def from_excel(cls, excel_fp: str) -> 'Params':
        """read params-file from excel"""
        self = cls.__new__(cls)
        with pd.ExcelFile(excel_fp) as excel:

            for k, v in cls.attr2tablename.items():
                sheet_name = v.replace('.', '_')[:30]
                df = pd.read_excel(excel, sheet_name)
                recarray = df.to_records()
                setattr(self, k, recarray)
        return self


def read_params_from_excel(param_file):
    params = Params.from_excel(param_file)
    return params


class Verkehrssystem(VisumTable):
    name = 'Verkehrssysteme'
    code = 'VSYS'

    _cols = ('CODE;TYP')


class BenutzerdefiniertesAttribut(VisumTable):
    name = 'Benutzerdefinierte Attribute'
    code = 'BENUTZERDEFATTRIBUTE'

    _cols = ('OBJID;ATTID;CODE;NAME;DATENTYP;MINWERT;MAXWERT;'
    'STANDARDWERT;STRINGSTANDARDWERT;KOMMENTAR;MAXSTRINGLAENGE;ANZDEZSTELLEN;'
    'DATENQUELLENTYP;FORMEL;QUERSCHNITTSLOGIK')

    _defaults = {'DATENTYP': 'Double',
                 'QUERSCHNITTSLOGIK': 'SUM',
                 'ANZDEZSTELLEN': 3,
                 'MAXSTRINGLAENGE': 255,
                 'MINWERT': 'MIN',
                 'MAXWERT': 'MAX',
                 }

    def add_formel_attribute(self,
                             objid,
                             name,
                             formel,
                             attid=None,
                             code=None,
                             **kwargs):
        """
        add Formel-Attribut

        Parameters
        ----------
        objid : str
            the network type like NETZ, AKTIVITAET etc.
        name : str
            the name of the attribute, will be used as code and attid, too
        formel : str
            the formula
        attid : str, optional
            the attid. If None, the name will be taken
        code : str, optional
            the code. If None, the name will be taken
        """
        attid = attid or name
        code = code or name
        row = self.Row(objid=objid,
                       datenquellentyp='FORMEL',
                       name=name,
                       attid=attid,
                       code=code,
                       formel=formel,
                       **kwargs)
        self.add_row(row)

    def add_daten_attribute(self,
                            objid,
                            name,
                            attid=None,
                            code=None,
                            **kwargs):
        """
        add Daten-Attribut

        Parameters
        ----------
        objid : str
            the network type like NETZ, AKTIVITAET etc.
        name : str
            the name of the attribute, will be used as code and attid, too
        attid : str, optional
            the attid. If None, the name will be taken
        code : str, optional
            the code. If None, the name will be taken
        """
        attid = attid or name
        code = code or name
        row = self.Row(objid=objid,
                       datenquellentyp='DATEN',
                       name=name,
                       attid=attid,
                       code=code,
                       **kwargs)
        self.add_row(row)


class Oberbezirk(VisumTable):
    name = 'Oberbezirke'
    code = 'OBERBEZIRK'
    _cols = 'NR;XKOORD;YKOORD'


class Bezirke(VisumTable):
    name = 'Bezirke'
    code = 'BEZIRK'
    _cols = 'NR'

    def read_pgr(self, fn):
        r = np.recfromtxt(open(fn, mode='rb').readlines(), delimiter=',',
                          names=True, filling_values=0)
        names = r.dtype.names[2:]
        attrs = ['NumPersons({})'.format(pg) for pg in names]
        self._cols = ';'.join(['NO'] + attrs)

        values = r[['vz_id']+list(names)]
        self.add_rows(values.tolist())
        self._mode = '*'

    def read_strukturdaten(self, fn):
        r = np.recfromtxt(open(fn, mode='rb').readlines(), delimiter=',',
                          names=True, filling_values=0)
        names = r.dtype.names[2:]
        attrs = ['ValStructuralProp({})'.format(sg.lstrip('ValStructuralProp'))
                 if sg.startswith('ValStructuralProp')
                 else sg
                 for sg in names]
        self._cols = ';'.join(['NO'] + list(attrs))

        values = r[['vz_id']+list(names)]
        self.add_rows(values.tolist())
        self._mode = '*'


class MatrixCategories(dict):
    _end_block = {'Visem_Demand': 20,
                  'Visem_OV_Stunden': 30,
                  'Other_Demand': 90,
                  'OV_Demand': 100,
                  'DestinationChoiceSkims': 110,
                  'IV_Skims': 150,
                  'IV_Skims_Parking': 200,
                  'OV_Skims_Fare': 250,
                  'OV_Skims_PJT': 700,
                  'Activities': 750,
                  'Activities_Balancing': 780,
                  'Commuters': 800,
                  'VL_Activities': 850,
                  'VL_Activities_OBB': 900,
                  'Activities_OBB': 1000,
                  'OV_TimeSeries_Skims_Formula': 1010,
                  'OV_TimeSeries_Skims': 2000,
                  'Demand_Pgr': 4000,
                  'Demand_Wiver': 4500,
                  'Demand_Wiver_OBB': 5000,
                  'OV_Demand_Activities': 5500,
                  'Modes_Demand_Activities': 6000,
                  'Demand_OV_Tagesgang': 6100,
                  'Demand_Verkehrsleistung': 7000,
                  'LogsumsPendler': 7500,
                  'Logsums': 9000,
                  'Accessibilities': 10000,
                  }

    def __init__(self):
        start_idx = 1
        for category, end_idx in sorted(
          self._end_block.items(), key=lambda x: x[1]):
            self[category] = iter(range(start_idx, end_idx))
            # next block starts where the last ends
            start_idx = end_idx


class Matrix(VisumTable):
    name = 'Matrizen'
    code = 'MATRIX'

    _cols = ('NR;CODE;NAME;MATRIXTYP;BEZUGSTYP;NSEGCODE;NSCHICHTSET;DATNAME;'
    'ANZDEZSTELLEN;DATENQUELLENTYP;FORMEL;TAG;VONZEIT;BISZEIT;ZEITBEZUG;'
    'MODUSCODE;MODUSSET;PERSONENGRUPPENSET;PGRUPPENCODE;AKTIVCODE;'
    'QUELLAKTIVITAETSET;ZIELAKTIVITAETSET;'
    'INITMATRIX;SAVEMATRIX;LOADMATRIX;MATRIXFOLDER;'
    'CALIBRATIONCODE;NACHFRMODELLCODE')

    _defaults = {'ANZDEZSTELLEN': 2,
                 'MATRIXTYP': 'Nachfrage',
                 'BEZUGSTYP': 'Bezirk',
                 'INITMATRIX': 0,
                 'SAVEMATRIX': 0,
                 'LOADMATRIX': 0,
                 }

    def __init__(self):
        super().__init__()
        self._number_block = MatrixCategories()

    def set_range(self, matrix_category: str):
        """Set of matrix numbers matrix_category"""
        self.matrix_numbers = self._number_block[matrix_category]

    def next_number(self) -> int:
        """Return next matrix number in range"""
        return next(self.matrix_numbers)

    def add_daten_matrix(self,
                         code: str,
                         name='',
                         loadmatrix=0,
                         matrixfolder='',
                         datname='',
                         **kwargs) -> int:
        """
        add Daten-Matrix

        Parameters
        ----------
        code : str
            the code of the matrix
        name : str, optional
            the name of the matrix. If not provided, the code is taken as name
        loadmatrix : int, optional(default=0)
            1 if matrix should be loaded
        matrixfolder : str, optional
            if given, read/write from Common Project folder, else from Scenario
        datname : str, optional
            the filename of the matrix on disk.
            If not provided, the code is taken as name

        Returns
        -------
        nr : int
            the number of the matrix inserted
        """
        name = name or code
        datname = datname or code
        nr = self.next_number()
        row = self.Row(nr=nr,
                       code=code,
                       name=name,
                       datenquellentyp='DATEN',
                       loadmatrix=loadmatrix,
                       matrixfolder=matrixfolder,
                       datname=datname,
                       **kwargs)
        self.add_row(row)
        return nr

    def add_formel_matrix(self,
                          code: str,
                          formel: str,
                          name='',
                          datname='',
                          **kwargs) -> int:
        """
        add Formel-Matrix

        Parameters
        ----------
        code : str
            the code of the matrix
        formel : str
            the formula
        name : str, optional
            the name of the matrix. If not provided, the code is taken as name
        datname : str, optional
            the filename of the matrix if it is stored on disk.
            If not provided, the code is taken as name
        **kwargs
            other columns

        Returns
        -------
        nr : int
            the number of the matrix inserted
       """
        name = name or code
        datname = datname or code
        nr = self.next_number()
        row = self.Row(nr=nr,
                       code=code,
                       formel=formel,
                       name=name,
                       loadmatrix=0,
                       datenquellentyp='FORMEL',
                       datname=datname,
                       **kwargs)
        self.add_row(row)
        return nr

    def get_timestring(self, hour: float) -> str:
        """
        convert hour into a time string in format HH:MM:SS
        """
        hour, minute, second = self._get_time_hour_minute_second(hour)
        t = datetime.time(hour, minute, second)
        return t.strftime('%H:%M:%S')

    def _get_time_hour_minute_second(self, hour):
        minute = (hour % 1) * 60
        hour = int(hour)
        if hour >= 24:
            hour = 23
            minute = 59
            second = 59
        else:
            second = round((minute % 1) * 60, 0)
            minute = int(minute)

        return hour, minute, second

    def get_time_seconds(self, hour: float) -> float:
        """
        convert hour into seconds since 00:00:00
        """
        hour, minute, second = self._get_time_hour_minute_second(hour)
        seconds = hour * 3600 + minute * 60 * + second
        return seconds

    def add_ov_kg_matrices(self,
                           params: Params,
                           userdefined: BenutzerdefiniertesAttribut,
                           savematrix=0,
                           factor=.8,
                           exponent=.8,
                           time_interval=1,
                           ):
        """Add OV Kenngrößen-Matrizen für Zeitscheiben"""
        time_series = params.time_series
        nsegcode = 'O'
        self.set_range('OV_TimeSeries_Skims')
        for ts in time_series:
            ts_code = ts['code']
            vonzeit = self.get_timestring(ts['from_hour'])
            biszeit = self.get_timestring(ts['to_hour'])
            self.add_daten_matrix(
                code='PJT',
                matrixtyp='Kenngröße',
                name='Empfundene Reisezeit {}'.format(nsegcode),
                datname='PJT_{}'.format(ts_code),
                nsegcode=nsegcode,
                tag=1,
                vonzeit=vonzeit,
                biszeit=biszeit,
                zeitbezug='Abfahrtszeit',
                initmatrix=1,
                #moduscode='O'
            )
            self.add_daten_matrix(
                code='FAR',
                matrixtyp='Kenngröße',
                name='Fahrpreis {}'.format(nsegcode),
                datname='FAR_{}'.format(ts_code),
                nsegcode=nsegcode,
                tag=1,
                vonzeit=vonzeit,
                biszeit=biszeit,
                initmatrix=1,
                zeitbezug='Abfahrtszeit',
                #moduscode='O',
            )
            self.add_daten_matrix(
                code='XADT',
                matrixtyp='Kenngröße',
                name='Erweiterte Anpassungszeit {}'.format(nsegcode),
                datname='XADT_{}'.format(ts_code),
                nsegcode=nsegcode,
                tag=1,
                vonzeit=vonzeit,
                biszeit=biszeit,
                initmatrix=1,
                zeitbezug='Abfahrtszeit',
                #moduscode='O',
            )
            self.add_daten_matrix(
                code='JRD',
                matrixtyp='Kenngröße',
                name='Reiseweite {}'.format(nsegcode),
                datname='JRD_{}'.format(ts_code),
                nsegcode=nsegcode,
                tag=1,
                vonzeit=vonzeit,
                biszeit=biszeit,
                initmatrix=1,
                zeitbezug='Abfahrtszeit',
                #moduscode='O',
            )

        self.add_daten_matrix(
            code='PJT',
            matrixtyp='Kenngröße',
            name='Empfundene Reisezeit {}'.format(nsegcode),
            nsegcode=nsegcode,
            vonzeit='',
            biszeit='',
            zeitbezug='Abfahrtszeit',
            #moduscode='O',
        )
        self.add_daten_matrix(
            code='FAR',
            matrixtyp='Kenngröße',
            name='Fahrpreis {}'.format(nsegcode),
            nsegcode=nsegcode,
            vonzeit='',
            biszeit='',
            zeitbezug='Abfahrtszeit',
            #moduscode='O',
        )
        self.add_daten_matrix(
            code='XADT',
            matrixtyp='Kenngröße',
            name='Erweiterte Anpassungszeit {}'.format(nsegcode),
            nsegcode=nsegcode,
            vonzeit='',
            biszeit='',
            zeitbezug='Abfahrtszeit',
            #moduscode='O',
        )

        self.set_range('OV_TimeSeries_Skims_Formula')

        self.add_formel_matrix(
            code='No_Connection_Forward',
            matrixtyp='Kenngröße',
            name='Keine ÖV-Verbindung in Zeitscheibe Hinweg',
            nsegcode=nsegcode,
            moduscode='O',
            formel=''
        )
        self.add_formel_matrix(
            code='No_Connection_Backward',
            matrixtyp='Kenngröße',
            name='Keine ÖV-Verbindung in Zeitscheibe Rückweg',
            nsegcode=nsegcode,
            moduscode='O',
            formel=''
        )
        self.add_formel_matrix(
            code='weighted_skim_matrix',
            matrixtyp='Kenngröße',
            name='Empfundene Reisezeit incl. SWZ, mit Aktivitäten gewichtet',
            nsegcode=nsegcode,
            moduscode='O',
            formel=''
        )
        # ÖV-Kosten
        self.set_range('OV_Skims_Fare')
        self.add_daten_matrix(
            code='SINGLETICKET',
            matrixtyp='Kenngröße',
            name='Fahrpreis Einzelticket',
            datname='Singelticket',
            nsegcode=nsegcode,
            moduscode='O',
            loadmatrix=1,
            savematrix=savematrix,
        )

        self.add_daten_matrix(
            code='JRD',
            matrixtyp='Kenngröße',
            name='Reiseweite {}'.format(nsegcode),
            nsegcode=nsegcode,
            vonzeit='',
            biszeit='',
            #initmatrix=1,
            zeitbezug='Abfahrtszeit',
            #moduscode='O',
        )

        self.add_daten_matrix(
            code='OVDIS',
            matrixtyp='Kenngröße',
            name='OV Reiseweite',
            datname='OVDIS',
            nsegcode=nsegcode,
            loadmatrix=1,
            savematrix=savematrix,
            moduscode='O',
        )

        userdefined.add_daten_attribute('Netz', 'DistanceKorrBisKm_OV',
                                         standardwert=3)
        userdefined.add_daten_attribute('Netz', 'DistanceKorrFaktor_OV',
                                         standardwert=-1.5)

        self.add_formel_matrix(
            code='DistanzKorrektur_OV',
            matrixtyp='Kenngröße',
            name='DistanzKorrektur_OV',
            datname='DistanzKorrektur_OV',
            moduscode='O',
            formel='(Matrix([CODE] = "KM") < [DistanceKorrBisKm_OV]) *'
            ' [DistanceKorrFaktor_OV] * '
            '([DistanceKorrBisKm_OV] - Matrix([CODE] = "KM"))',
        )

        # ÖV-Nachfragematrizen nach Zeitscheiben
        self.set_range('OV_TimeSeries_Skims_Formula')

        # PJT_All-Matrix für nur eine Zeitscheibe
        ts = time_series[time_interval]
        ts_code = ts['code']
        vonzeit = self.get_time_seconds(ts['from_hour'])
        biszeit = self.get_time_seconds(ts['to_hour'])
        formula = (
            'Matrix([CODE] = "PJT" & [FROMTIME]={f} & [TOTIME]={t}) + '
            '{factor} * POW('
            '(Matrix([CODE] = "XADT" & [FROMTIME]={f} & [TOTIME]={t}) * 4 + 1)'
            ', {exponent})')
        formula2 = formula.format(f=vonzeit,
                                  t=biszeit,
                                  factor=factor,
                                  exponent=exponent)
        complete_formula = '(({f}) + TRANSPOSE({f})) * 0.5'.format(f=formula2)

        self.add_formel_matrix(
            code='PJT_All',
            matrixtyp='Kenngröße',
            name='Empfundene Reisezeit alle Aktivitäten',
            nsegcode=nsegcode,
            formel=complete_formula,
        )

    def add_iv_kg_matrices(self,
                           userdefined: BenutzerdefiniertesAttribut,
                           savematrix=0):
        """Add PrT Skim Matrices"""
        self.set_range('IV_Skims')
        self.add_daten_matrix(code='DIS', name='Fahrweite Pkw', loadmatrix=1,
                              matrixtyp='Kenngröße',
                              nsegcode='P',
                              #moduscode='P',
                              vonzeit='',
                              biszeit='',
                              savematrix=savematrix)
        self.add_daten_matrix(code='TFUSS', name='tFuss', loadmatrix=1,
                              matrixtyp='Kenngröße',
                              nsegcode='F',
                              moduscode='F',
                              savematrix=savematrix)
        self.add_daten_matrix(code='TRAD', name='tRad', loadmatrix=1,
                              matrixtyp='Kenngröße',
                              nsegcode='R',
                              moduscode='R',
                              savematrix=savematrix)
        self.add_daten_matrix(code='TT0', name='t0 Pkw', loadmatrix=1,
                              matrixtyp='Kenngröße',
                              nsegcode='P',
                              vonzeit='',
                              biszeit='',
                              #moduscode='P',
                              savematrix=savematrix)
        self.add_daten_matrix(code='TTC', name='tAkt Pkw', loadmatrix=1,
                              matrixtyp='Kenngröße',
                              nsegcode='P',
                              vonzeit='',
                              biszeit='',
                              #moduscode='P',
                              savematrix=savematrix)
        self.add_daten_matrix(code='TTC_boxcox',
                              name='tAkt Pkw BoxCox-Transformiert',
                              loadmatrix=1,
                              matrixtyp='Kenngröße',
                              nsegcode='P',
                              moduscode='P',
                              savematrix=savematrix)

        userdefined.add_formel_attribute(
            objid='Bezirk',
            name='Binnendistanz_area',
            formel='SQRT([FLAECHEKM2]) / 3',
            kommentar='geschätzte Binnendistanz in km',
                                    )

        self.add_formel_matrix(
            code='PkwKosten',
            matrixtyp='Kenngröße',
            nsegcode='P',
            name='Pkw Fahrtkosten',
            formel='Matrix([CODE] = "DIS" & [NSEGCODE] = "P") * '
                   '[COST_PER_KM_PKW]')

        self.add_formel_matrix(code='SFUSS', name='sFuss',
                               matrixtyp='Kenngröße',
                               nsegcode='F',
                               moduscode='F',
                               formel='Matrix([CODE] = "TFUSS") * 4.5 / 60')

        formel = ('If (Matrix([CODE] = "TFUSS") > 100.0 ,'
                  'If(Matrix([CODE] = "TRAD") < 999.0 ,'
                  'Matrix([CODE] = "TRAD") * 16 / 60.0,'
                  'Matrix([CODE] = "DIS")),'
                  'Matrix([CODE] = "SFUSS"))')
        self.add_formel_matrix(code='KM', name='Reiseweite',
                                   matrixtyp='Kenngröße',
                                   formel=formel)


        userdefined.add_daten_attribute('Netz', 'DistanceKorrBisKm_Pkw',
                                             standardwert=1.2)
        userdefined.add_daten_attribute('Netz', 'DistanceKorrFaktor_Pkw',
                                             standardwert=-4)

        self.add_formel_matrix(
                code='DistanzKorrektur_Pkw',
                matrixtyp='Kenngröße',
                name='DistanzKorrektur_Pkw',
                datname='DistanzKorrektur_Pkw',
                moduscode='P',
                formel='(Matrix([CODE] = "KM") < [DistanceKorrBisKm_Pkw]) *'
                ' [DistanceKorrFaktor_Pkw] * '
                '([DistanceKorrBisKm_Pkw] - Matrix([CODE] = "KM"))',
            )


    def add_iv_demand(self, savematrix=0, loadmatrix=1):
        """Add PrT Demand Matrices"""
        self.set_range('Visem_Demand')
        self.add_daten_matrix(code='Visem_P', name='Pkw regional',
                              loadmatrix=loadmatrix,
                              matrixtyp='Nachfrage',
                              nsegcode='P',
                              moduscode='P',
                              savematrix=savematrix)

        self.set_range('Other_Demand')
        self.add_daten_matrix(code='Pkw_Wirtschaftsverkehr',
                              name='Pkw-Wirtschaftsverkehr',
                              loadmatrix=loadmatrix,
                              matrixtyp='Nachfrage',
                              nsegcode='B_P',
                              moduscode='P')
        self.add_daten_matrix(code='Lieferfahrzeuge', name='Lieferfahrzeuge',
                              loadmatrix=loadmatrix,
                              matrixtyp='Nachfrage',
                              nsegcode='B_Li',
                              moduscode='P')
        self.add_daten_matrix(code='Lkw_bis_12to',
                              name='Lkw zw. 3,5 und 12 to',
                              loadmatrix=loadmatrix,
                              matrixtyp='Nachfrage',
                              nsegcode='B_L1',
                              moduscode='L')
        self.add_daten_matrix(code='Lkw_über_12to', name='Lkw > 3,5 to',
                              loadmatrix=loadmatrix,
                              matrixtyp='Nachfrage',
                              nsegcode='B_L2',
                              moduscode='L')
        self.add_daten_matrix(code='FernverkehrPkw',
                              name='Pkw-Fernverkehr',
                              loadmatrix=loadmatrix,
                              matrixtyp='Nachfrage',
                              nsegcode='PkwFern',
                              moduscode='P')
        self.add_daten_matrix(code='FernverkehrLkw',
                              name='Lkw-Fernverkehr',
                              loadmatrix=loadmatrix,
                              matrixtyp='Nachfrage',
                              nsegcode='LkwFern',
                              moduscode='L')

        # Summen Schwerverkehr und Kfz bis 3.5 to
        nsegs = ['Lkw_bis_12to',
                 'Lkw_über_12to',
                 'FernverkehrLkw']
        formel = ' + '.join(('Matrix([CODE]="{}")'.format(nseg)
                            for nseg in nsegs))
        self.add_formel_matrix(code='Schwerverkehr',
                               formel=formel,
                               name='Schwerverkehr ohne Busse',
                               matrixtyp='Nachfrage',
                               nsegcode='SV',
                               moduscode='L')

        nsegs = ['Visem_P',
                 'Pkw_Wirtschaftsverkehr',
                 'Lieferfahrzeuge',
                 'FernverkehrPkw']
        formel = ' + '.join(('Matrix([CODE]="{}")'.format(nseg)
                             for nseg in nsegs))
        self.add_formel_matrix(code='Kfz_35',
                               formel=formel,
                               name='Kfz bis 3,5 to',
                               matrixtyp='Nachfrage',
                               nsegcode='Kfz_35',
                               moduscode='P')

    def add_ov_demand(self, savematrix=0, loadmatrix=1):
        """Add PrT Demand Matrices"""
        self.set_range('Visem_Demand')
        self.add_daten_matrix(code='Visem_O', name='ÖPNV',
                              loadmatrix=loadmatrix,
                              matrixtyp='Nachfrage',
                              nsegcode='O',
                              moduscode='O',
                              savematrix=savematrix)
        self.set_range('OV_Demand')
        self.add_daten_matrix(code='FernverkehrBahn', name='Fernverkehr Bahn',
                              loadmatrix=loadmatrix,
                              matrixtyp='Nachfrage',
                              nsegcode='OFern',
                              moduscode='O')

    def add_other_demand_matrices(self,
                                  params: Params,
                                  loadmatrix=1,
                                  savematrix=1):
        """Add Demand Matrices for other modes"""
        self.set_range('Visem_Demand')
        existing_codes = self.table.CODE

        self.add_daten_matrix(code='Visem_Gesamt',
                              name='Fahrten incl. Einpendler',
                              loadmatrix=loadmatrix,
                              savematrix=savematrix,
                              matrixtyp='Nachfrage')

        for mode in params.modes:
            code = mode['code']
            mode_name = mode['name']
            matname = 'Fahrten {} incl. Einpendler'.format(mode_name)
            matcode = 'Visem_{}'.format(code)
            if matcode not in existing_codes:
                self.add_daten_matrix(code=matcode,
                                      name=matname,
                                      loadmatrix=loadmatrix,
                                      matrixtyp='Nachfrage',
                                      moduscode=code,
                                      savematrix=savematrix,
                                      )

        self.add_daten_matrix(code='Demand_Total',
                              name='Fahrten Regionsbewohner',
                              loadmatrix=loadmatrix,
                              matrixtyp='Nachfrage')


        for mode in params.modes:
            code = mode['code']
            matcode = 'Demand_{}'.format(code)
            mode_name = mode['name']
            name = 'Fahrten {} Regionsbewohner'.format(mode_name)
            if matcode not in existing_codes:
                self.add_daten_matrix(code=matcode,
                                      name=name,
                                      loadmatrix=loadmatrix,
                                      matrixtyp='Nachfrage',
                                      moduscode=code,
                                      )

        self.add_daten_matrix(code='Demand_Total_OBB',
                              name='Fahrten Regionsbewohner Oberbezirk',
                              loadmatrix=loadmatrix,
                              matrixtyp='Nachfrage',
                              bezugstyp='Oberbezirk')

        for mode in params.modes:
            code = mode['code']
            matcode = 'Demand_{}_OBB'.format(code)
            mode_name = mode['name']
            name = 'Fahrten {} Regionsbewohner Oberbezirk'.format(mode_name)
            if matcode not in existing_codes:
                self.add_daten_matrix(code=matcode,
                                      name=name,
                                      loadmatrix=loadmatrix,
                                      matrixtyp='Nachfrage',
                                      moduscode=code,
                                      bezugstyp='Oberbezirk')

        self.set_range('Demand_Verkehrsleistung')
        for mode in params.modes:
            distance_matrix = mode['distance_matrix']
            code = mode['code']
            matcode = 'VL_{}'.format(code)
            mode_name = mode['name']
            matname = 'Verkehrsleistung incl. Einpendler{}'.format(mode_name)
            if matcode not in existing_codes:
                formel = 'Matrix([CODE]="Visem_{c}") * Matrix([CODE]="{dm}")'.\
                    format(c=code, dm=distance_matrix)
                self.add_formel_matrix(code=matcode,
                                       name=matname,
                                       formel=formel,
                                       matrixtyp='Nachfrage',
                                       moduscode=code,
                                       )
            # add Verkehrsleistungs-Formelmatrix ohne Einpendler
            matcode = 'VL_Region_{}'.format(code)
            mode_name = mode['name']
            matname = 'Verkehrsleistung ohne Einpendler {}'.format(mode_name)
            if matcode not in existing_codes:
                formel = 'Matrix([CODE]="Demand_{c}") * Matrix([CODE]="{dm}")'.\
                    format(c=code, dm=distance_matrix)
                self.add_formel_matrix(code=matcode,
                                       name=matname,
                                       formel=formel,
                                       matrixtyp='Nachfrage',
                                       moduscode=code,
                                       )


    def add_ov_haupt_ap_demand_matrices(self,
                                        ds_tagesgang: xr.Dataset,
                                        loadmatrix=0,
                                        savematrix=1):
        """Add Demand Matrices for other modes"""
        self.set_range('Demand_OV_Tagesgang')
        for hap in ds_tagesgang.hap:
            matcode = 'Visem_OV_{}'.format(hap.lab_hap.values)
            self.add_daten_matrix(code=matcode,
                                  loadmatrix=loadmatrix,
                                  matrixtyp='Nachfrage',
                                  moduscode='O',
                                  savematrix=savematrix,
                                  )

    def add_commuter_matrices(self, userdefined: BenutzerdefiniertesAttribut,
                              loadmatrix=1,
                              savematrix=1):
        """Add Commuter Matrices"""
        self.set_range('Commuters')
        self.add_daten_matrix(code='Pendlermatrix_modelliert',
                              name='Pendlermatrix modelliert',
                              loadmatrix=loadmatrix,
                              savematrix=savematrix,
                              matrixtyp='Nachfrage')
        self.add_daten_matrix(code='Pendler_OBB_modelliert',
                              name='Pendlermatrix Oberbezirk modelliert',
                              loadmatrix=loadmatrix,
                              savematrix=savematrix,
                              matrixtyp='Nachfrage',
                              bezugstyp='Oberbezirk')
        self.add_daten_matrix(code='Pendlermatrix',
                              name='Pendlermatrix',
                              loadmatrix=1,
                              matrixtyp='Nachfrage',
                              matrixfolder='Pendler')
        self.add_daten_matrix(code='Pendlermatrix_OBB',
                              name='Pendlermatrix',
                              bezugstyp='Oberbezirk',
                              matrixtyp='Nachfrage',
                              loadmatrix=1,
                              matrixfolder='Pendler')
        userdefined.add_daten_attribute(objid='Netz',
                                        name='faktor_binnenpendler',
                                        standardwert=1.28)
        userdefined.add_daten_attribute(objid='Netz',
                                        name='faktor_einpendler',
                                        standardwert=1.430976)
        userdefined.add_daten_attribute(objid='Netz',
                                        name='faktor_auspendler',
                                        standardwert=1.27264235846709)
        formel = '''Matrix([CODE]="Pendlermatrix_OBB") * '''\
        '''((FROM[TYPNR] = 0) * [faktor_einpendler] + (FROM[TYPNR] = 1)) * '''\
        '''((TO[TYPNR] = 0) * [faktor_auspendler] + (TO[TYPNR] = 1)) * '''\
        '''((FROM[TYPNR] = 1) * (TO[TYPNR] = 1) * [faktor_binnenpendler] + '''\
        '''(FROM[TYPNR] = 0) * (TO[TYPNR] = 1) + '''\
        '''(FROM[TYPNR] = 1) * (TO[TYPNR] = 0))'''
        self.add_formel_matrix(
            code='Pendlermatrix_OBB_Gesamt',
            name='Pendlermatrix_OBB incl Nicht-SVB-Beschäftigte',
            matrixtyp='Nachfrage',
            bezugstyp='Oberbezirk',
            matrixfolder='Pendler',
            savematrix=1,
            formel=formel)

        self.set_range('DestinationChoiceSkims')
        self.add_formel_matrix(
            code='Aussen2Aussen',
            matrixtyp='Kenngröße',
            formel='-999999 * (FROM[TYPNR] > 3) * (TO[TYPNR] > 3)')
        self.add_formel_matrix(
            code='Innen2Aussen',
            matrixtyp='Kenngröße',
            formel='-999999 * ((FROM[TYPNR] <= 3) * (TO[TYPNR] <= 3) + (FROM[TYPNR] > 3) * (TO[TYPNR] > 3))')

    def add_logsum_matrices(self,
                            demand_strata:'Nachfrageschicht',
                            actchains:'AKTIVITAETENKETTE',
                            matrix_range='Logsums',
                            ):
        """Add logsum matrices for each person group and main activity"""

        self.set_range(matrix_range)
        ketten = {a['CODE']: a['AKTIVCODES'].split(',')[1: -1]
                  for a in actchains.table}
        pgr_activities = defaultdict(set)
        for ns in demand_strata.table:
            pgr = ns['PGRUPPENCODES']
            nachfragemodellcode = ns['NACHFRAGEMODELLCODE']
            if nachfragemodellcode in ('VisemT', 'Pendler'):
                activities = pgr_activities[(nachfragemodellcode, pgr)]
                new_activities = ketten[ns['AKTKETTENCODE']]
                for activity in new_activities:
                    activities.add(activity)
        for (nmc, pgr), activities in pgr_activities.items():
            for activity in activities:
                code = 'LogsumMatrix'
                name = 'Logsum {p} {a}'.format(p=pgr, a=activity)
                self.add_daten_matrix(
                    code,
                    name,
                    matrixtyp='Kenngröße',
                    loadmatrix=0,
                    savematrix=0,
                    initmatrix=1,
                    nachfrmodellcode=nmc,
                    pgruppencode=pgr,
                    aktivcode=activity,
                    )




class Nachfragemodell(VisumTable):
    name = 'Nachfragemodelle'
    code = 'NACHFRAGEMODELL'
    _cols = 'CODE;NAME;TYP;MODUSSET'

    def add_model(self,
                  params: Params,
                  code: str,
                  name='',
                  DemandModelType='VISEM'):
        row = self.Row(code=code,
                       name=name,
                       typ=DemandModelType,
                       modusset=params.mode_set)
        self.add_row(row)


class Personengruppe(VisumTable):
    name = 'Personengruppen'
    code = 'PERSONENGRUPPE'
    _cols = 'CODE;NAME;NACHFRAGEMODELLCODE;ACTCHAIN;CAR_AVAILABILITY;GROUPDESTMODE;OCCUPATION;VOTT'
    _defaults = {'VOTT': 10}

    def __init__(self):
        super(Personengruppe, self).__init__()
        self.groups = []
        self.gd_codes = {}

    def add_group(self, code: str, modellcode: str, **kwargs):
        row = self.Row(code=code,
                       nachfragemodellcode=modellcode,
                       **kwargs)
        self.groups.append(row)

    def add_group_generation(self, code: str, name: str, groupdestmode):
        self.add_group(code, name=name, modellcode='VisemGeneration',
                       groupdestmode=groupdestmode)

    def add_group_destmode(self, code: str, name: str, groupdestmode,
                           actchain, car_availability, occupation):
        self.add_group(code, name=name, modellcode='VisemT',
                       actchain=actchain,
                       car_availability=car_availability,
                       occupation=occupation,
                       groupdestmode=groupdestmode)

    def create_table(self):
        self.table = self.table_from_array(self.groups)

    def create_groups_generation(self, params: Params):
        # sort person group by code
        person_groups = params.gg
        for p in person_groups:
            self.add_group_generation(code=p['code'],
                                      name=p['code'],
                                      groupdestmode=p['group_dest_mode'])

    def create_groups_destmode(self,
                               params: Params,
                               file_aufteilung_arbeitswege: str,
                               activities: 'Aktivitaet'):
        """"""
        assert isinstance(activities, Aktivitaet)
        act_hierarchy = activities.get_hierarchy()
        person_groups = params.gd
        person_groups = person_groups[person_groups['code'].argsort()]
        trip_chain_rates = params.trip_chain_rates
        gg = params.gg
        gg = gg[gg['code'].argsort()]
        gg_idx = np.searchsorted(gg['code'], trip_chain_rates['group_generation'])
        ggd = gg['group_dest_mode'][gg_idx]
        gds = np.unique(np.rec.fromarrays([ggd, trip_chain_rates['code']],
                                          names=['gd', 'actcode']),)
        gd_idx = np.searchsorted(person_groups['code'], gds['gd'])
        self.gd_codes = {}
        for g, tc in enumerate(gds):
            gd_code = tc['gd']
            act_code = tc['actcode']
            main_act = activities.get_main_activity(act_hierarchy, act_code)
            code = '_'.join((gd_code, main_act))
            if code not in self.gd_codes:
                self.gd_codes[code] = [act_code]
                name = code
                gdd = person_groups[gd_idx[g]]
                self.add_group_destmode(
                    code=code,
                    name=name,
                    groupdestmode=gd_code,
                    car_availability=gdd['car_availability'],
                    occupation=gdd['occupation'],
                    actchain=main_act)
            else:
                self.gd_codes[code].append(act_code)

    def add_calibration_matrices_and_attributes(
          self,
          params: Params,
          matrices: Matrix,
          userdefined: BenutzerdefiniertesAttribut):
        """
        Add Output Matrices for PersonGroups
        """
        matrices.set_range('Demand_Pgr')
        calibration_defs = ['occupation', 'car_availability']
        modes = params.mode_set.split(',')
        for cg in calibration_defs:
            calibration_groups = np.unique(self.table[cg.upper()])
            for group in calibration_groups:
                if group:
                    gr_code = '{g}_{o}'.format(g=cg, o=group)
                    for mode in modes:
                        # add output matrix
                        str_name = 'Wege mit Verkehrsmittel {m} der Gruppe {g}'
                        matrices.add_daten_matrix(
                            code='{g}_{m}'.format(g=gr_code, m=mode),
                            name=str_name.format(g=gr_code, m=mode),
                            moduscode=mode,
                            calibrationcode=gr_code)

                    # Alternativenspezifische Konstante im Modell
                    userdefined.add_daten_attribute(
                        objid='MODUS',
                        name='Const_{g}'.format(g=gr_code))

                    # Wege nach Modus und Modal Split der Gruppe
                    formel = 'TableLookup(MATRIX Mat: Mat[CODE]="{g}_"+[CODE]: Mat[SUMME])'
                    userdefined.add_formel_attribute(
                        objid='MODUS',
                        name='Trips_{g}'.format(g=gr_code),
                        formel=formel.format(g=gr_code),
                        kommentar='Gesamtzahl der Wege der Gruppe {g}'.format(
                            g=gr_code),
                    )
                    # Wege Gesamt der Gruppe
                    userdefined.add_formel_attribute(
                        objid='NETZ',
                        name='Trips_{g}'.format(g=gr_code),
                        formel='[SUM:MODI\Trips_{g}]'.format(
                            g=gr_code),
                        kommentar='Gesamtzahl der Wege der Gruppe {g}'.format(
                            g=gr_code),
                    )
                    # Modal Split der Gruppe
                    userdefined.add_formel_attribute(
                        objid='MODUS',
                        name='MS_{g}'.format(g=gr_code),
                        formel='[Trips_{g}] / [NETZ\Trips_{g}]'.format(
                            g=gr_code),
                        kommentar='Modal Split der Gruppe {g}'.format(
                            g=gr_code),
                    )

                    # Ziel-Modal Split der Gruppe
                    userdefined.add_daten_attribute(
                        objid='Modus',
                        name='Target_MS_{g}'.format(g=gr_code),)

        # Wege nach Modus und Modal Split Gesamt
        userdefined.add_formel_attribute(
            objid='MODUS',
            name='Trips_Region',
            formel='TableLookup(MATRIX Mat: Mat[CODE]="Demand_"+[CODE]: Mat[SUMME])',
            kommentar='Gesamtzahl der Wege der Regionsbewohner',
        )
        # Wege Gesamt der Regionsbewohner
        userdefined.add_formel_attribute(
            objid='NETZ',
            name='Trips_Region',
            formel='[SUM:MODI\Trips_Region]',
            kommentar='Gesamtzahl der Wege der Regionsbewohner',
        )
        # Modal Split der Regionsbewohner
        userdefined.add_formel_attribute(
            objid='MODUS',
            name='MS_Regionsbewohner',
            formel='[Trips_Region] / [NETZ\Trips_Region]',
            kommentar='Modal Split der Regionsbewohner',
        )

        # Wege nach Modus und Modal Split Gesamt
        gr_code = 'Demand'
        userdefined.add_formel_attribute(
            objid='MODUS',
            name='Trips_RegionMitEinpendler',
            formel='TableLookup(MATRIX Mat: Mat[CODE]="Visem_"+[CODE]: Mat[SUMME])',
            kommentar='Gesamtzahl der Wege der Regionsbewohner incl. Einpendler',
        )
        # Wege Gesamt der Regionsbewohner
        gr_code = 'Total'
        userdefined.add_formel_attribute(
            objid='NETZ',
            name='Trips_RegionMitEinpendler',
            formel='[SUM:MODI\Trips_RegionMitEinpendler]',
            kommentar='Gesamtzahl der Regionsbewohner',
        )
        # Modal Split der Regionsbewohner
        userdefined.add_formel_attribute(
            objid='MODUS',
            name='MS_Trips_RegionMitEinpendler',
            formel='[Trips_RegionMitEinpendler] / [NETZ\Trips_RegionMitEinpendler]',
            kommentar='Modal Split incl. Einpendler',
        )

        # Ziel Entfernung nach Verkehrsmittel
        userdefined.add_daten_attribute(
            objid='Modus',
            name='Target_MEAN_DISTANCE',
            anzdezstellen=2,
        )


class Strukturgr(VisumTable):
    name = 'Strukturgrößen'
    code = 'STRUKTURGROESSE'
    _cols = 'CODE;NAME;NACHFRAGEMODELLCODE'

    def create_tables(self,
                      params: Params,
                      model: str,
                      suffix=''):
        rows = []
        for a in params.activities:
            row = self.Row(nachfragemodellcode=model)
            row.code = a['potential'] + suffix
            row.name = a['name']
            rows.append(row)
        self.add_rows(rows)


class Strukturgroessenwert(VisumTable):
    name = 'Strukturgrößenwerte'
    code = 'STRUKTURGROESSENWERT'
    _cols = 'BEZNR;STRUKTURGROESSENCODE;WERT'


class PersonengruppeJeBezirk(VisumTable):
    name = 'Personengruppe je Bezirk'
    code = 'PERSONENGRUPPEJEBEZIRK'
    _cols = 'BEZNR;PGRUPPENCODE;ANZPERSONEN'


class Nachfragebeschreibung(VisumTable):
    name = 'Nachfragebeschreibungen'
    code = 'NACHFRAGEBESCHREIBUNG'
    _cols = 'NSEGCODE;NACHFRAGEGLNR;MATRIX'
    _defaults = {'NACHFRAGEGLNR': 1}


class Aktivitaet(VisumTable):
    name = 'Aktivitäten'
    code = 'AKTIVITAET'
    _cols = ('CODE;RANG;NAME;NACHFRAGEMODELLCODE;ISTHEIMATAKTIVITAET;'
             'STRUKTURGROESSENCODES;KOPPLUNGZIEL;RSA;BASE_CODE')

    def create_tables(self,
                      params: Params,
                      model: str,
                      suffix=''):
        rows = []
        for a in params.activities:
            row = self.Row(nachfragemodellcode=model)
            row.code = a['code'] + suffix
            row.name = a['name']
            row.strukturgroessencodes = a['potential'] + suffix
            is_home_activity = row.code.startswith('W')
            row.rang = a['rank'] or 1
            row.rsa = a['balance']
            row.istheimataktivitaet = is_home_activity
            row.kopplungziel = is_home_activity
            row.base_code = row.code[0]
            rows.append(row)
        self.add_rows(rows)

    def get_main_activity(self, hierarchy, ac_code):
        """get the code of the main activity from ac_code

        Parameters
        ----------
        hierarchy : dict
            the hierarchy-dict produced by self.get_hierarchy()
        ac_code : str
            the Activity-Chain like WAEW

        Returns
        -------
        main_activity : str
        """
        main_act = ac_code[np.argmin(np.array([hierarchy[a]
                                               for a in ac_code]))]
        return main_act

    def get_hierarchy(self):
        """
        Return a dict with the hierarchy of activities

        Returns
        -------
        hierarchy : dict
        """
        a = self.table
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', FutureWarning)
            argsort = np.argsort(a[['RANG', 'CODE']])
        hierarchy = a['CODE'][argsort][a['ISTHEIMATAKTIVITAET'][argsort] == 0]
        h = dict(zip(hierarchy, range(len(hierarchy))))
        idx = len(h)
        for act in a[a['ISTHEIMATAKTIVITAET'] == 1]:
            h[act['CODE']] = idx
        return h

    def add_benutzerdefinierte_attribute(
          self,
          userdefined: BenutzerdefiniertesAttribut):
        """
        Add benutzerdefinierte Attribute for Activities
        """
        userdefined.add_formel_attribute(
            objid='AKTIVITAET',
            name='TotalTripsRegion',
            formel='TableLookup(MATRIX Mat: '
            'Mat[CODE]="Activity_"+[CODE]: Mat[SUMME])',
            kommentar='Gesamtzahl der Wege'
        )
        userdefined.add_formel_attribute(
            objid='AKTIVITAET',
            name='TotalTrips',
            formel='TableLookup(MATRIX Mat: '
            'Mat[CODE]="AllActivity_"+[CODE]: Mat[SUMME])',
        )
        userdefined.add_formel_attribute(
            objid='AKTIVITAET',
            name='TripDistance',
            formel='TableLookup(MATRIX Mat: '
            'Mat[CODE]="VL_Activity_"+[CODE]: Mat[SUMME]) / [TotalTripsRegion]',
        )
        userdefined.add_formel_attribute(
            objid='MODUS',
            name='TripDistance',
            formel='TableLookup(MATRIX Mat: '
            'Mat[CODE]="VL_"+[CODE]: Mat[SUMME]) / [Trips_RegionMitEinpendler]',
        )
        userdefined.add_formel_attribute(
            objid='MODUS',
            name='TripDistanceRegion',
            formel='TableLookup(MATRIX Mat: '
            'Mat[CODE]="VL_Region_"+[CODE]: Mat[SUMME]) / [Trips_Region]',
        )

        userdefined.add_daten_attribute(
            objid='AKTIVITAET',
            name='TTFACTOR_O',
            kommentar='Anpassung Reisezeitkoeffizient ÖV für Aktivität',
            standardwert=1,
        )
        userdefined.add_daten_attribute(
            objid='AKTIVITAET',
            name='TTFACTOR_M',
            kommentar='Anpassung Reisezeitkoeffizient Mitfahrer für Aktivität',
            standardwert=1,
        )

    def add_output_matrices(self,
                            matrices: Matrix,
                            userdefined: BenutzerdefiniertesAttribut, ):
        """
        Add Output Matrices for Activities
        """
        self.matrixnummern_activity = {}
        for t in self.table:
            if not t.CODE.endswith('_'):
                name = t.NAME

                matrices.set_range('Activities')
                nr = matrices.add_daten_matrix(
                    code='Activity_{}'.format(t.CODE),
                    name='Gesamtzahl der Wege zu Aktivität {}'.format(name),
                    aktivcode=t.CODE,
                )

                matrices.set_range('VL_Activities')
                nr_vl = matrices.add_formel_matrix(
                    code='VL_Activity_{}'.format(t.CODE),
                    name='Fahrleistung Aktivität {}'.format(name),
                    formel='Matrix([CODE] = "Activity_{}") * '
                    'Matrix([CODE] = "KM")'.format(t.CODE),
                    aktivcode=t.CODE,
                )

                # Distanz nach Wohnort
                userdefined.add_formel_attribute(
                    'BEZIRK',
                    name='Distance_WohnOrt_{}'.format(t.CODE),
                    formel='[MATZEILENSUMME({vl:d})] / [MATZEILENSUMME({wege:d})]'.\
                    format(vl=nr_vl, wege=nr),
                )
                userdefined.add_formel_attribute(
                    'BEZIRK',
                    name='Distance_AktOrt_{}'.format(t.CODE),
                    formel='[MATSPALTENSUMME({vl:d})] / [MATSPALTENSUMME({wege:d})]'.\
                    format(vl=nr_vl, wege=nr),
                )

                #  Wege und Verkehrsleistung nach Oberbezirk
                matrices.set_range('Activities_OBB')
                obb_nr = matrices.add_daten_matrix(
                    code='Activity_{}_OBB'.format(t.CODE),
                    name='Oberbezirks-Matrix Aktivität {}'.format(name),
                    aktivcode=t.CODE,
                    bezugstyp='Oberbezirk',
                )
                matrices.set_range('VL_Activities_OBB')
                vl_obb_nr = matrices.add_daten_matrix(
                    code='Activity_VL_{}_OBB'.format(t.CODE),
                    name='Oberbezirks-Matrix VL Aktivität {}'.format(name),
                    aktivcode=t.CODE,
                    bezugstyp='Oberbezirk',
                )

                userdefined.add_formel_attribute(
                    'OBERBEZIRK',
                    name='Distance_WohnOrt_{}'.format(t.CODE),
                    formel='[MATZEILENSUMME({vl:d})] / [MATZEILENSUMME({wege:d})]'.\
                    format(vl=vl_obb_nr,
                           wege=obb_nr),
                )
                userdefined.add_formel_attribute(
                    'OBERBEZIRK',
                    name='Distance_AktOrt_{}'.format(t.CODE),
                    formel='[MATSPALTENSUMME({vl:d})] / [MATSPALTENSUMME({wege:d})]'.\
                    format(vl=vl_obb_nr,
                           wege=obb_nr),
                )
                self.matrixnummern_activity[t.CODE] = nr

                if t.ISTHEIMATAKTIVITAET:
                    self.matrixnummer_activity_w = nr
                    self.matrixnummer_activity_vl_w = nr_vl
                    self.obbmatrixnummer_activity_w = obb_nr
                    self.obbmatrixnummer_activity_vl_w = vl_obb_nr

                if t.RSA:
                    matrices.set_range('Commuters')
                    matrices.add_daten_matrix(
                        code='Pendler_{}_OBB'.format(t.CODE),
                        name='Oberbezirks-Matrix Pendleraktivität {}'.format(name),
                        aktivcode=t.CODE,
                        bezugstyp='Oberbezirk',
                    )

    def add_balancing_output_matrices(self,
                                      matrices: Matrix,
                                      userdefined: BenutzerdefiniertesAttribut,
                                      loadmatrix=0,
                                      savematrix=1):
        """
        Add Output Matrices for Activities with Balancing
        """
        converged_attributes = []
        matrices.set_range('Activities_Balancing')
        for t in self.table:
            code = t.CODE
            if not code.endswith('_'):
                name = t.NAME

                matrices.set_range('Activities')
                nr = matrices.add_daten_matrix(
                    code='AllActivity_{}'.format(code),
                    name='Gesamtzahl der Gesamtwege zu Aktivität {}'.format(name),
                    aktivcode=code,
                    savematrix=savematrix,
                    loadmatrix=loadmatrix,
                )

                if t.RSA:
                    matrices.set_range('Commuters')
                    nr = matrices.add_daten_matrix(
                        code='Pendler_{}'.format(code),
                        name='Gesamtzahl der PendlerGesamtwege zu Aktivität {}'.format(name),
                        aktivcode=code,
                        savematrix=savematrix,
                        loadmatrix=loadmatrix,
                    )
                    # Add KF-Attribute
                    userdefined.add_formel_attribute(
                        objid='BEZIRK',
                        attid='ZONE_ACTUAL_TRIPS_{}'.format(code),
                        formel='[MATSPALTENSUMME({:d})]'.format(nr),
                        code='Trips_actual_to {}'.format(code),
                        name='Actual Trips to Zone for Activity {}'.format(code),
                        )

                    name = t.NAME
                    userdefined.add_daten_attribute(
                        objid='BEZIRK',
                        name='ZP0_{}'.format(code),
                        kommentar='Basis-Zielpotenzial für Aktivität {}'.format(code)
                    )
                    userdefined.add_daten_attribute(
                        objid='BEZIRK',
                        name='BF_{}'.format(code),
                        kommentar='Bilanzfaktor für Aktivität {}'.format(code),
                        standardwert=1,
                    )

                    # Ziel-Wege je Bezirk
                    formel = '[ZP0_{a}] / [NETZ\SUM:BEZIRKE\ZP0_{a}] * [NETZ\SUM:BEZIRKE\ZONE_ACTUAL_TRIPS_{a}]'
                    userdefined.add_formel_attribute(
                        objid='BEZIRK',
                        attid='ZONE_TARGET_TRIPS_{}'.format(code),
                        code='Target Trips to Zone for {}'.format(code),
                        name='Target Trips to zone for Activity {}'.format(code),
                        formel=formel.format(a=code)
                    )

                    # Korrekturfaktor
                    formel = 'IF([ZONE_ACTUAL_TRIPS_{a}]>0, [ZONE_TARGET_TRIPS_{a}] / [ZONE_ACTUAL_TRIPS_{a}], 1)'
                    userdefined.add_formel_attribute(
                        objid='BEZIRK',
                        attid='ZONE_KF_{}'.format(code),
                        code='Zonal Korrekturfaktor {}'.format(code),
                        name='Zonal Korrekturfaktor for Activity {}'.format(code),
                        kommentar='Bilanzfaktor für Aktivität {}'.format(code),
                        formel=formel.format(a=code)
                    )

                    # converged
                    threshold_min = 0.95
                    threshold_max = 1.05
                    formel = '[MIN:BEZIRKE\ZONE_KF_{a}] < {min} | [MAX:BEZIRKE\ZONE_KF_{a}] > {max}'
                    attid = 'NOT_CONVERGED_{a}'.format(a=code)
                    userdefined.add_formel_attribute(
                        objid='NETZ',
                        datentyp='Bool',
                        attid=attid,
                        code=attid,
                        name='Randsummenabgleich nicht konvergiert für Aktivität {a}'.format(a=code),
                        formel=formel.format(a=code,
                                             min=threshold_min,
                                             max=threshold_max))
                    converged_attributes.append(attid)

        formel = ' | '.join(("[{}]".format(c) for c in converged_attributes))
        attid = 'NOT_CONVERGED_ANY_ACTIVITY'
        userdefined.add_formel_attribute(
            objid='NETZ',
            datentyp='Bool',
            attid=attid,
            code=attid,
            name='Randsummenabgleich nicht konvergiert für mindestens eine Aktivität',
            formel=formel)

        userdefined.add_daten_attribute(
            objid='NETZ',
            name='NOT_CONVERGED_MS_TRIPLENGTH',
            datentyp='Bool',
            standardwert=1,
            kommentar='Modal Split und Wegelängen sind noch nicht konvergiert')

    def add_pjt_matrices(self,
                         matrices: Matrix,
                         savematrix=0):
        """
        Add Percieved Journey Time Matrices for Activities
        """
        matrices.set_range('OV_Skims_PJT')
        for t in self.table:
            if not t.CODE.endswith('_') and not t.ISTHEIMATAKTIVITAET and not t.CODE == 'Y':
                name = t.NAME
                matrices.add_daten_matrix(
                    code='PJT_{}'.format(t.CODE),
                    name='Empfundene Reisezeit für Hauptaktivität {}'.format(name),
                    matrixtyp='Kenngröße',
                    aktivcode=t.CODE,
                    loadmatrix=1,
                    savematrix=savematrix,
                )

    def add_parking_matrices(self,
                             matrices: Matrix,
                             savematrix=0):
        """
        Add Parking Matrices for Activities
        """
        matrices.set_range('IV_Skims_Parking')
        for t in self.table:
            if not t.CODE.endswith('_') and not t.ISTHEIMATAKTIVITAET and not t.CODE == 'Y':
                name = t.NAME
                matrices.add_daten_matrix(
                    code='PARKING_{}'.format(t.CODE),
                    name='Parkwiderstand für Hauptaktivität {}'.format(name),
                    aktivcode=t.CODE,
                    matrixtyp='Kenngröße',
                    loadmatrix=1,
                    savematrix=savematrix,
                )

    def add_net_activity_ticket_attributes(self,
                                           userdefined: BenutzerdefiniertesAttribut):
        """Add userdefined attributes for ticket costs"""
        formel_ov = 'TableLookup(ACTIVITY Act: Act[CODE]="{a}": Act[HRF_EINZEL2ZEITKARTE])'
        formel_time_ov = 'TableLookup(ACTIVITY Act: Act[CODE]="{a}": Act[TTFACTOR_O])'
        formel_cost_mitfahrer = 'TableLookup(ACTIVITY Act: Act[CODE]="{a}": Act[HRF_COST_MITFAHRER])'
        formel_time_mitfahrer = 'TableLookup(ACTIVITY Act: Act[CODE]="{a}": Act[TTFACTOR_M])'

        for t in self.table:
            if not t.CODE.endswith('_') and not t.ISTHEIMATAKTIVITAET and not t.CODE == 'Y':
                userdefined.add_formel_attribute(
                    'NETZ',
                    name='Factor_Ticket_{}'.format(t.CODE),
                    formel=formel_ov.format(a=t.CODE)
                )
                userdefined.add_formel_attribute(
                    'NETZ',
                    name='Factor_Time_OV_{}'.format(t.CODE),
                    formel=formel_time_ov.format(a=t.CODE)
                )
                userdefined.add_formel_attribute(
                    'NETZ',
                    name='Factor_Cost_Mitfahrer_{}'.format(t.CODE),
                    formel=formel_cost_mitfahrer.format(a=t.CODE)
                )
                userdefined.add_formel_attribute(
                    'NETZ',
                    name='Factor_Time_Mitfahrer_{}'.format(t.CODE),
                    formel=formel_time_mitfahrer.format(a=t.CODE)
                )
    def add_modal_split(self,
                        userdefined: BenutzerdefiniertesAttribut,
                        matrices: Matrix,
                        params: Params):
        """Add userdefined attributes and Matrices for modal split by actiity"""
        formel_trips = 'TableLookup(MATRIX Mat, Mat[CODE]="Activity_{a}_"+[CODE], Mat[SUM])'
        formel_ms = '[TRIPS_ACTIVITY_{a}] / [NETZ\TRIPS_ACTIVITY_{a}]'
        formel_netz_trips = '[SUM:MODI\TRIPS_ACTIVITY_{a}]'

        matrices.set_range('Modes_Demand_Activities')

        for t in self.table:
            if not t.CODE.endswith('_'):
                init_matrix = 0 if t.ISTHEIMATAKTIVITAET else 1
                for mode in params.modes:
                    matrices.set_range('Modes_Demand_Activities')

                    mode_code = mode['code']
                    # add output matrix
                    str_name = 'Wege mit Verkehrsmittel {m} der für Aktivität {a}'
                    nr = matrices.add_daten_matrix(
                        code='Activity_{a}_{m}'.format(a=t.CODE, m=mode_code),
                        name=str_name.format(a=t.CODE, m=mode_code),
                        moduscode=mode_code,
                        aktivcode=t.CODE,
                        initmatrix=init_matrix,
                    )

                    userdefined.add_formel_attribute(
                        'BEZIRK',
                        name='MS_{}_Act_{}'.format(mode_code, t.CODE),
                        formel='[MATSPALTENSUMME({nr:d})] / [MATSPALTENSUMME({ges:d})]'.\
                        format(nr=nr, ges=self.matrixnummern_activity[t.CODE]),
                    )

                    if t.ISTHEIMATAKTIVITAET:
                        # add output Oberbezirks-Matrix
                        str_name = 'OBB-Wege mit Verkehrsmittel {m} der für Aktivität {a}'
                        nr_obb = matrices.add_daten_matrix(
                            code='OBB_Activity_{a}_{m}'.format(a=t.CODE, m=mode_code),
                            name=str_name.format(a=t.CODE, m=mode_code),
                            moduscode=mode_code,
                            aktivcode=t.CODE,
                            bezugstyp='Oberbezirk',
                            initmatrix=0,
                        )

                        userdefined.add_formel_attribute(
                            'OBERBEZIRK',
                            name='MS_Home_Mode_{}'.format(mode_code),
                            formel='[MATSPALTENSUMME({nr:d})] / [MATSPALTENSUMME({ges:d})]'.\
                            format(nr=nr_obb,
                                   ges=self.obbmatrixnummer_activity_w),
                        )
                        userdefined.add_formel_attribute(
                            'BEZIRK',
                            name='MS_Home_Mode_{}'.format(mode_code),
                            formel='[MATSPALTENSUMME({nr:d})] / [MATSPALTENSUMME({ges:d})]'.\
                            format(nr=nr, ges=self.matrixnummer_activity_w),
                        )

                        # add Verkehrsleistung
                        matrices.set_range('VL_Activities')
                        formel = 'Matrix([CODE]="Activity_{a}_{m}") * Matrix([CODE] = "KM")'
                        nr_vl = matrices.add_formel_matrix(
                            code='VL_Activity_{a}_{m}'.format(a=t.CODE, m=mode_code),
                            name=str_name.format(a=t.CODE, m=mode_code),
                            moduscode=mode_code,
                            aktivcode=t.CODE,
                            formel=formel.format(a=t.CODE, m=mode_code),
                            bezugstyp='Bezirk',
                            initmatrix=0,
                        )
                        matrices.set_range('VL_Activities_OBB')
                        nr_obb_vl = matrices.add_daten_matrix(
                            code='OBB_VL_Activity_{a}_{m}'.format(a=t.CODE, m=mode_code),
                            name=str_name.format(a=t.CODE, m=mode_code),
                            moduscode=mode_code,
                            aktivcode=t.CODE,
                            bezugstyp='Oberbezirk',
                            initmatrix=0,
                        )
                        userdefined.add_formel_attribute(
                            'OBERBEZIRK',
                            name='Distance_Home_{}'.format(mode_code),
                            formel='[MATZEILENSUMME({vl:d})] / [MATZEILENSUMME({wege:d})]'.\
                            format(vl=nr_obb_vl,
                                   wege=nr_obb),
                        )
                        userdefined.add_formel_attribute(
                            'BEZIRK',
                            name='Distance_Home_{}'.format(mode_code),
                            formel='[MATZEILENSUMME({vl:d})] / [MATZEILENSUMME({wege:d})]'.\
                            format(vl=nr_vl, wege=nr),
                        )

                userdefined.add_daten_attribute(
                    'MODUS',
                    name='Target_MS_activity_{}'.format(t.CODE),
                )
                userdefined.add_daten_attribute(
                    'MODUS',
                    name='const_activity_{}'.format(t.CODE),
                    standardwert=0,
                )
                userdefined.add_formel_attribute(
                    'MODUS',
                    name='Trips_activity_{}'.format(t.CODE),
                    formel=formel_trips.format(a=t.CODE)
                )
                userdefined.add_formel_attribute(
                    'Netz',
                    name='TRIPS_ACTIVITY_{}'.format(t.CODE),
                    formel=formel_netz_trips.format(a=t.CODE)
                )
                userdefined.add_formel_attribute(
                    'MODUS',
                    name='MS_activity_{}'.format(t.CODE),
                    formel=formel_ms.format(a=t.CODE)
                )

    def add_kf_logsum(self,
                      userdefined: BenutzerdefiniertesAttribut,
                      ):
        """
        add Korrekturfaktoren für Logsum-Formeln auf Oberbezirksebene
        Dieser werden dann auf Bezirksebene übertragen und im
        Zielwahlmodell zur Korrektur der Wegelängen verwendet
        """
        reference_column = 'OBERBEZIRK_SRV'
        formel = 'TableLookup(MAINZONE OBB, OBB[NO]=[{col}], OBB[KF_LOGSUM_{a}])'
        for t in self.table:
            if not (t.CODE.endswith('_') or t.ISTHEIMATAKTIVITAET):
                userdefined.add_daten_attribute(
                    'Oberbezirk',
                    'kf_logsum_{}'.format(t.CODE),
                    standardwert=1,
                )

                userdefined.add_formel_attribute(
                    'Bezirk',
                    'kf_logsum_{}'.format(t.CODE),
                    formel=formel.format(col=reference_column,
                                         a=t.CODE),
                )


class Aktivitaetenpaar(VisumTable):
    name = 'Aktivitätenpaare'
    code = 'AKTIVITAETENPAAR'
    _cols = 'CODE;NAME;NACHFRAGEMODELLCODE;QUELLAKTIVITAETCODE;ZIELAKTIVITAETCODE;QUELLEZIELTYP'
    _pkey = 'CODE'
    _defaults = {'QUELLZIELTYP': 3,
                 }

    def create_tables(self,
                      params: Params,
                      model: str,
                      suffix=''):
        rows = []
        for a in params.activitypairs:
            ap_code = a['code']
            origin_code = ap_code[0] + suffix
            dest_code = ap_code[1] + suffix
            ap_new_code = origin_code + dest_code
            row = self.Row(code=ap_new_code,
                           name=ap_code,
                           nachfragemodellcode=model,
                           quellaktivitaetcode=origin_code,
                           zielaktivitaetcode=dest_code)
            rows.append(row)
        self.add_rows(rows)


class Aktivitaetenkette(VisumTable):
    name = 'Aktivitätenketten'
    code = 'AKTIVITAETENKETTE'
    _cols = 'CODE;NAME;NACHFRAGEMODELLCODE;AKTIVCODES'
    _pkey = 'CODE'

    def create_tables(self, params: Params,
                      model: str,
                      suffix=''):
        rows = []
        activity_chains = np.unique(params.trip_chain_rates['code'])
        for activity_chain in activity_chains:
            ac = activity_chain
            act_seq = ['{c}{s}'.format(c=a, s=suffix) for a in ac]
            code = ''.join(act_seq)
            act_chain_sequence = ','.join(act_seq)
            row = self.Row(code=code,
                           name=ac,
                           nachfragemodellcode=model,
                           aktivcodes=act_chain_sequence)
            rows.append(row)
        self.add_rows(rows)


class Nachfrageschicht(VisumTable):
    name = 'Nachfrageschichten'
    code = 'NACHFRAGESCHICHT'
    _cols = 'CODE;NAME;NACHFRAGEMODELLCODE;AKTKETTENCODE;PGRUPPENCODES'

    def create_tables_gg(self,
                         params: Params,
                         model='VisemGeneration',
                         suffix='_'):
        rows = []
        for tcr in params.trip_chain_rates:
            row = self.Row(nachfragemodellcode=model)
            pgr_code = tcr['group']
            ac = tcr['code']
            act_seq = ('{c}{s}'.format(c=a, s=suffix) for a in ac)
            ac_code = ''.join(act_seq)
            row.name = '_'.join((pgr_code, ac))
            if model == 'VisemT':
                row.code = name
            else:
                row.code = '_'.join([pgr_code, ac_code])
            row.aktkettencode = ac_code
            row.pgruppencodes = pgr_code
            rows.append(row)
        self.add_rows(rows)

    def create_tables_gd(self,
                         params: Params,
                         personengruppe: Personengruppe,
                         model='VisemT'):
        rows = []
        pg_table = personengruppe.table
        pg_gd = pg_table[pg_table['NACHFRAGEMODELLCODE'] == model]
        for gd in pg_gd:
            code = gd['CODE']
            pgr_code = gd['GROUPDESTMODE']
            main_act = gd['ACTCHAIN']
            for ac_code in personengruppe.gd_codes[code]:
                row = self.Row(nachfragemodellcode=model,
                               pgruppencodes=code,
                               aktkettencode=ac_code)
                row.code = '_'.join((pgr_code, ac_code))
                row.name = row.code
                rows.append(row)
        self.add_rows(rows)


class Ganglinienelement(VisumTable):
    name = 'Ganglinieneinträge'
    code = 'GANGLINIENELEMENT'
    _cols = 'GANGLINIENNR;STARTZEIT;ENDZEIT;GEWICHT;MATRIX'


class Nachfrageganglinie(VisumTable):
    name = 'NACHFRAGEGANGLINIE'
    code = 'NACHFRAGEGANGLINIE'
    _cols = 'NR;CODE;NAME;GANGLINIENNR'


class VisemGanglinie(VisumTable):
    name = 'VISEM-Ganglinien'
    code = 'VISEMGANGLINIE'
    _cols = 'AKTPAARCODE;PGRUPPENCODE;GANGLINIENNR'


class Ganglinie(VisumTable):
    name = 'Ganglinien'
    code = 'GANGLINIE'
    _cols = 'NR;NAME;WERTETYP'
    _defaults = {'WERTETYP': 'Anteile'}

    def create_tables(self,
                      params: Params,
                      ganglinienelement: Ganglinienelement,
                      nachfrageganglinie: Nachfrageganglinie,
                      visem_ganglinie: VisemGanglinie,
                      personengruppe: Personengruppe,
                      start_idx=100,
                      ):

        rows = []
        rows_ganglinienelement = []
        rows_nachfrageganglinien = []
        rows_visem_nachfrageganglinien = []
        aps = params.activitypairs
        time_series = params.time_series
        ap_timeseries_recarray = params.activitypair_time_series
        ap_timeseries = ap_timeseries_recarray.view(dtype='f8').\
            reshape(-1, 25)[:, 1:]
        for a, ap in enumerate(aps):
            ap_code = ap['code']
            idx = ap['idx']
            nr = idx + start_idx
            row = self.Row(nr=nr, name=ap_code)
            rows.append(row)

            # Nachfrageganglinie
            row_nachfrageganglinie = nachfrageganglinie.Row(
                nr=nr, code=ap_code, name=ap_code, gangliniennr=nr)
            rows_nachfrageganglinien.append(row_nachfrageganglinie)

            # Ganglinie
            ap_timeserie = ap_timeseries[idx]
            for ts in time_series:
                from_hour = ts['from_hour']
                to_hour = ts['to_hour']
                anteil = ap_timeserie[from_hour:to_hour].sum()
                if anteil:
                    row_ganglinienelement = ganglinienelement.Row(
                        gangliniennr=nr,
                        startzeit=from_hour * 3600,
                        endzeit=to_hour * 3600,
                        gewicht=anteil)
                    rows_ganglinienelement.append(row_ganglinienelement)

            # Personengruppen
            for pg in personengruppe.table:
                row_visem_ganglinie = visem_ganglinie.Row(
                    pgruppencode=pg['CODE'], gangliniennr=nr)
                if pg['NACHFRAGEMODELLCODE'] == 'VisemGeneration':
                    apg_code = '{}_{}_'.format(ap_code[0], ap_code[1])
                    row_visem_ganglinie.aktpaarcode = apg_code
                else:
                    row_visem_ganglinie.aktpaarcode = ap_code
                rows_visem_nachfrageganglinien.append(row_visem_ganglinie)

        self.add_rows(rows)
        ganglinienelement.add_rows(rows_ganglinienelement)
        nachfrageganglinie.add_rows(rows_nachfrageganglinien)
        visem_ganglinie.add_rows(rows_visem_nachfrageganglinien)


class Nachfragesegment(VisumTable):
    name = 'Nachfragesegments'
    code = 'NACHFRAGESEGMENT'
    _cols = 'CODE;NAME;MODUS'
    _defaults = {'MODUS': 'L'}

    def add_ov_ganglinien(self,
                          ds_ganglinie: xr.Dataset,
                          ganglinie:Ganglinie,
                          ganglinienelement: Ganglinienelement,
                          nachfrageganglinie: Nachfrageganglinie,
                          nachfrage_beschr:Nachfragebeschreibung,
                          start_idx:int=80,
                          ):
        """Add Ganglinien for OV"""
        modus = 'O'
        rows_nseg = []
        rows_ganglinie = []
        rows_ganglinienelement = []
        rows_nachfrageganglinien = []
        rows_nachfragebeschreibung = []
        gl = ds_ganglinie.ganglinie
        ds_ganglinie['anteile_stunde'] = gl / gl.sum('stunde')

        for hap in ds_ganglinie.hap:
            hap_name = hap.lab_hap.values
            mat_code = 'Visem_OV_{}'.format(hap_name)

            nsg_code = 'OV_{}'.format(hap_name)
            nseg_name = 'OV {}'.format(hap_name)

            hap_id = hap.hap.values
            nachfr_gl_nr = gl_nr = hap_id + start_idx
            gl_name = 'OV_{}'.format(hap_name)
            rows_ganglinie.append(ganglinie.Row(nr=gl_nr, name=gl_name))

            row_nachfrageganglinie = nachfrageganglinie.Row(
                nr=nachfr_gl_nr, code=gl_name, name=gl_name,
                gangliniennr=gl_nr)
            rows_nachfrageganglinien.append(row_nachfrageganglinie)

            gl_stunde = ds_ganglinie.anteile_stunde.sel(hap=hap_id)

            for stunde in gl_stunde:
                # in sekunden, Intervalle von 60 sec.
                startzeit = stunde.stunde * 3600
                endzeit = startzeit + 3600
                if stunde:
                    row_ganglinienelement = ganglinienelement.Row(
                        gangliniennr=gl_nr,
                        startzeit=startzeit,
                        endzeit=endzeit,
                        gewicht=stunde)
                    rows_ganglinienelement.append(row_ganglinienelement)

            matrix_descr = 'MATRIX([CODE]="{}")'.format(mat_code)
            rows_nseg.append(self.Row(code=nsg_code,
                                      name=nseg_name,
                                      modus=modus))
            rows_nachfragebeschreibung.append(nachfrage_beschr.Row(
                nsegcode=nsg_code,
                nachfrageglnr=nachfr_gl_nr,
                matrix=matrix_descr
            ))

        self.add_rows(rows_nseg)
        ganglinie.add_rows(rows_ganglinie)
        nachfrageganglinie.add_rows(rows_nachfrageganglinien)
        ganglinienelement.add_rows(rows_ganglinienelement)
        nachfrage_beschr.add_rows(rows_nachfragebeschreibung)


def write_modification_iv_matrices(modification_number=12, modifications):
    v = VisumTransfer.new_transfer()

    matrices = Matrix()
    matrices.add_iv_demand()
    v.tables['Matrizen'] = matrices
    v.write(fn=v.get_modification(modification_number, modifications))


def write_modification_ov_matrices(modification_number=14, modifications):
    v = VisumTransfer.new_transfer()

    matrices = Matrix()
    matrices.add_ov_demand()
    v.tables['Matrizen'] = matrices
    v.write(fn=v.get_modification(modification_number, modifications))


def main(modification_number=5, modifications):
    add_nsegs_userdefined()


    v = VisumTransfer.new_transfer()

    ## read original data from hdf5
    #params = read_params(param_file)
    ## convert to Excel
    #params.save2excel(param_excel_fp)

    # use the data from the excel-file
    params = Params.from_excel(param_excel_fp)

    userdefined1 = BenutzerdefiniertesAttribut()
    v.tables['BenutzerdefinierteAttribute1'] = userdefined1
    userdefined2 = BenutzerdefiniertesAttribut()

    matrices = Matrix()
    matrices_logsum = Matrix()

    m = Nachfragemodell()
    m.add_model(params, 'VisemGeneration', name='Visem-Erzeugungsmodell')
    m.add_model(params, 'VisemT', name='Visem Ziel- und Verkehrsmittelwahlmodell')
    v.tables['Nachfragemodell'] = m

    sg = Strukturgr()
    sg.create_tables(params, model='VisemGeneration', suffix='_')
    sg.create_tables(params, model='VisemT', suffix='')
    v.tables['Strukturgr'] = sg

    ac = Aktivitaet()
    userdefined1.add_daten_attribute('Aktivitaet', 'RSA', datentyp='Bool')
    userdefined1.add_daten_attribute('Aktivitaet', 'Base_Code',
                                     datentyp='Text')

    ac.create_tables(params, model='VisemGeneration', suffix='_')
    ac.create_tables(params, model='VisemT', suffix='')
    ac.add_benutzerdefinierte_attribute(userdefined2)
    ac.add_net_activity_ticket_attributes(userdefined2)
    ac.add_output_matrices(matrices, userdefined2)
    ac.add_modal_split(userdefined2, matrices, params)
    ac.add_balancing_output_matrices(matrices, userdefined2, loadmatrix=0)
    ac.add_parking_matrices(matrices)
    ac.add_pjt_matrices(matrices)
    ac.add_kf_logsum(userdefined2)
    v.tables['Aktivitaet'] = ac

    pg = Personengruppe()
    userdefined1.add_daten_attribute('Personengruppe', 'ACTCHAIN',
                                     datentyp='Text')
    userdefined1.add_daten_attribute('Personengruppe', 'CAR_AVAILABILITY',
                                     datentyp='Text')
    userdefined1.add_daten_attribute('Personengruppe', 'GROUPDESTMODE',
                                     datentyp='Text')
    userdefined1.add_daten_attribute('Personengruppe', 'OCCUPATION',
                                     datentyp='Text')
    userdefined1.add_daten_attribute('Personengruppe', 'VOTT')
    pg.create_groups_generation(params)
    pg.create_groups_destmode(params, file_aufteilung_arbeitswege, ac)
    pg.create_table()
    pg.add_calibration_matrices_and_attributes(params, matrices, userdefined2)
    v.tables['PersonGroups'] = pg

    ap = Aktivitaetenpaar()
    ap.create_tables(params, model='VisemGeneration', suffix='_')
    ap.create_tables(params, model='VisemT', suffix='')
    v.tables['Aktivitaetenpaar'] = ap

    ak = Aktivitaetenkette()
    ak.create_tables(params, model='VisemGeneration', suffix='_')
    ak.create_tables(params, model='VisemT', suffix='')
    v.tables['Aktivitaetenkette'] = ak

    ns = Nachfrageschicht()
    ns.create_tables_gd(params,
                        personengruppe=pg,
                        model='VisemT')
    v.tables['Nachfrageschicht'] = ns

    # Kenngrößenmatrizen
    matrices.add_ov_kg_matrices(params, userdefined1)
    matrices.add_iv_kg_matrices(userdefined1)
    matrices.add_iv_demand(loadmatrix=1)
    matrices.add_ov_demand(loadmatrix=1)
    matrices.add_other_demand_matrices(params, loadmatrix=0)
    matrices.add_commuter_matrices(userdefined1)

    # Verkehrssysteme mit FV-Präferenz
    vsys = Verkehrssystem(mode='*')
    define_vsys_fv_preference(vsys, userdefined2)

    # add matrices later
    v.tables['Matrizen'] = matrices
    v.tables['BenutzerdefinierteAttribute2'] = userdefined2
    v.tables['Verkehrssysteme'] = vsys

    #userdefined2.add_logsum_kf(userdefined2)
    #matrices_logsum.add_logsum_matrices(ns, ak)
    #v.tables['MatrizenLogsum'] = matrices_logsum

    gl = Ganglinie()
    gle = Ganglinienelement()
    ngl = Nachfrageganglinie()
    vgl = VisemGanglinie()
    gl.create_tables(params, gle, ngl, vgl, pg)

    v.tables['Ganglinie'] = gl
    v.tables['Ganglinienelement'] = gle
    v.tables['VisemGanglinien'] = vgl

    v.write(fn=v.get_modification(modification_number, modifications))

def add_nsegs_userdefined(modification_no:int = 4, modifications):
    v = VisumTransfer.new_transfer()
    userdefined0 = BenutzerdefiniertesAttribut()
    v.tables['BenutzerdefinierteAttribute0'] = userdefined0

    # Matrizen
    userdefined0.add_daten_attribute('Matrix', 'INITMATRIX', datentyp='Bool')
    userdefined0.add_daten_attribute('Matrix', 'LOADMATRIX', datentyp='Bool')
    userdefined0.add_daten_attribute('Matrix', 'SAVEMATRIX', datentyp='Bool')
    userdefined0.add_daten_attribute('Matrix', 'MATRIXFOLDER',
                                     datentyp='Text')
    userdefined0.add_daten_attribute('Matrix', 'CALIBRATIONCODE',
                                     datentyp='Text')

    # Netzattribute
    userdefined0.add_daten_attribute('Netz', 'COST_PER_KM_PKW',
                                     standardwert=0.15)
    userdefined0.add_daten_attribute('Netz',
                                     'FilenameFactorsCommuters',
                                     datentyp='Text',
                                     stringstandardwert="Factors_Commuters.csv")
    userdefined0.add_daten_attribute('Netz',
                                     'FilenameTripChainRates',
                                     datentyp='Text',
                                     stringstandardwert="tcr_gg.csv")
    userdefined0.add_daten_attribute('Netz', 'MINUS_ONE', standardwert=-1)

    # Aktivitäten
    userdefined0.add_daten_attribute('Aktivitaet', 'HRF_EINZEL2ZEITKARTE',
                                     standardwert=1.0)
    userdefined0.add_daten_attribute('Aktivitaet', 'HRF_COST_MITFAHRER',
                                     standardwert=1.0)
    userdefined0.add_daten_attribute('Aktivitaet', 'LS',
                                     standardwert=1.0)

    # Bezirk
    userdefined0.add_daten_attribute('Bezirk', 'OBERBEZIRK_SRV')
    userdefined0.add_daten_attribute('Bezirk', 'ANTEIL_FERNAUSPENDLER',
                                     standardwert=0.0)


    # Nachfragesegmente
    nseg = Nachfragesegment()
    v.tables['Nachfragesegment'] = nseg
    #nseg.add_row(nseg.Row(code='O', name='ÖV Region', modus='O'))
    nseg.add_row(nseg.Row(code='OFern', name='ÖV Fernverkehr', modus='O'))
    nseg.add_row(nseg.Row(code='B_P', name='Pkw-Wirtschaftsverkehr',
                          modus='P'))
    nseg.add_row(nseg.Row(code='B_Li', name='Lieferfahrzeug',
                          modus='P'))
    nseg.add_row(nseg.Row(code='B_L1', name='Lkw bis 12 to',
                          modus='L'))
    nseg.add_row(nseg.Row(code='B_L2', name='Lkw 12-40 to',
                          modus='L'))
    nseg.add_row(nseg.Row(code='LkwFern', name='Lkw Fernverkehr',
                          modus='L'))
    nseg.add_row(nseg.Row(code='PkwFern', name='Pkw Fernverkehr',
                          modus='P'))
    nseg.add_row(nseg.Row(code='SV', name='Schwerverkehr',
                          modus='L'))
    nseg.add_row(nseg.Row(code='Kfz_35', name='Kfz bis 3,5 to',
                          modus='P'))

    v.write(fn=v.get_modification(modification_no, modifications))


def define_vsys_fv_preference(vsys: Verkehrssystem,
                              userdefined2: BenutzerdefiniertesAttribut):
    userdefined2.add_daten_attribute('VSYS', 'VSYS_FV_PREFERENCE', standardwert=1)
    vsys.add_cols(['VSYS_FV_PREFERENCE'])
    #row = vsys.Row(code='FAE', typ='OV', vsys_fv_preference=0.2)
    #vsys.add_row(row)
    row = vsys.Row(code='S', typ='OV', vsys_fv_preference=0.5)
    vsys.add_row(row)

if __name__ == '__main__':
    add_nsegs_userdefined(4)
    main(5)
    #write_modification_iv_matrices(12)
    #write_modification_ov_matrices(14)
