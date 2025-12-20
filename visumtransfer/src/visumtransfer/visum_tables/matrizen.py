# -*- coding: utf-8 -*-

import datetime
from collections import defaultdict
import xarray as xr
from visumtransfer.params import Params
from typing import Mapping, List
from .basis import UserDefinedAttribute
from visumtransfer.visum_table import VisumTable


class MatrixCategories(dict):
    _end_block: Mapping[str, int] = {
        'General': 5,
        'Visem_Demand': 20,
        'Visem_OV_Stunden': 30,
        'Other_Demand': 90,
        'OV_Demand': 100,
        'DestinationChoiceSkims': 108,
        'IV_Skims': 150,
        'IV_Skims_Parking': 200,
        'OV_Skims_Fare': 250,
        'OV_Skims_PJT': 700,
        'Activities': 800,
        'Activities_Homebased': 900,
        'Activities_Balancing': 1000,
        'Commuters': 1100,
        'VL_Activities': 1200,
        'VL_Activities_Homebased': 1300,
        'Activities_Modellierungsraum': 1400,
        'VL_Activities_Modellierungsraum': 1500,
        'VL_Activities_OBB': 1600,
        'Activities_OBB': 1700,
        'OV_TimeSeries_Skims_Formula': 1800,
        'OV_TimeSeries_Skims': 2000,
        'Demand_Pgr': 4000,
        'VL_Pgr': 6000,
        'Demand_Wiver': 7000,
        'Demand_Wiver_OBB': 7500,
        'OV_Demand_Activities': 8000,
        'Modes_Demand_Activities': 9000,
        'Demand_OV_Tagesgang': 10000,
        'Demand_Verkehrsleistung': 12000,
        'LogsumsPendler': 12000,
        'Logsums': 15000,
        'Accessibilities': 20000,
    }

    def __init__(self):
        start_idx = 1
        for category, end_idx in sorted(
          self._end_block.items(), key=lambda x: x[1]):
            self[category] = iter(range(start_idx, end_idx))
            # next block starts where the last ends
            start_idx = end_idx
        self['_fallback'] = iter(range(start_idx, 9999999))


class Matrix(VisumTable):
    name = 'Matrizen'
    code = 'MATRIX'
    matrix_category = ''

    _cols = ('NO;CODE;NAME;MATRIXTYPE;OBJECTTYPEREF;DSEGCODE;DSTRATSET;FILENAME;'
             'NUMDECPLACES;DATASOURCETYPE;FORMULA;DAY;FROMTIME;TOTIME;TIMEREF;'
             'MODECODE;MODESET;PERSONGROUPSET;PERSONGROUPCODE;ACTIVITYCODE;'
             'ORIGACTIVITYSET;DESTACTIVITYSET;'
             'INITMATRIX;SAVEMATRIX;LOADMATRIX;MATRIXFOLDER;'
             'CALIBRATIONCODE;NACHFRMODELLCODE;CATEGORY;OBB_MATRIX_REF')

    _defaults = {'NUMDECPLACES': 2,
                 'MATRIXTYPE': 'Nachfrage',
                 'OBJECTTYPEREF': 'Bezirk',
                 'INITMATRIX': 0,
                 'SAVEMATRIX': 0,
                 'LOADMATRIX': 0,
                 }

    def __init__(self):
        super().__init__()
        self._number_block = MatrixCategories()

    def set_category(self, matrix_category: str):
        """Set set matrix_category"""
        self.matrix_category = matrix_category

    @property
    def matrix_numbers(self) -> MatrixCategories:
        return self._number_block[self.matrix_category]

    def next_number(self) -> int:
        """Return next matrix number in range"""
        try:
            no = next(self.matrix_numbers)
        except StopIteration:
            no = next(self._number_block['_fallback'])
        return no

    def add_daten_matrix(self,
                         code: str,
                         name='',
                         loadmatrix=0,
                         matrixfolder='',
                         filename='',
                         category: str = None,
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
        filename : str, optional
            the filename of the matrix on disk.
            If not provided, the code is taken as name
        category : str, optional
            the matrix category. If not given,
            use the category last set by set_category()

        Returns
        -------
        no : int
            the number of the matrix inserted
        """
        name = name or code
        filename = filename or code
        no = self.next_number()
        self.add(no=no,
                 code=code,
                 name=name,
                 datasourcetype='DATEN',
                 loadmatrix=loadmatrix,
                 matrixfolder=matrixfolder,
                 filename=filename,
                 category=category or self.matrix_category,
                 ** kwargs)
        return no

    def add_formel_matrix(self,
                          code: str,
                          formula: str,
                          name='',
                          filename='',
                          category: str = None,
                          **kwargs) -> int:
        """
        add formula-Matrix

        Parameters
        ----------
        code : str
            the code of the matrix
        formula : str
            the formula
        name : str, optional
            the name of the matrix. If not provided, the code is taken as name
        filename : str, optional
            the filename of the matrix if it is stored on disk.
            If not provided, the code is taken as name
        category : str, optional
            the matrix category. If not given,
            use the category last set by set_category()
        **kwargs
            other columns

        Returns
        -------
        no : int
            the number of the matrix inserted
       """
        name = name or code
        filename = filename or code
        no = self.next_number()
        self.add(no=no,
                 code=code,
                 formula=formula,
                 name=name,
                 loadmatrix=0,
                 datasourcetype='FORMULA',
                 filename=filename,
                 category=category or self.matrix_category,
                 **kwargs)
        return no

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
            second = int(round((minute % 1) * 60, 0))
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
                           userdef: UserDefinedAttribute,
                           savematrix=0,
                           factor=.8,
                           exponent=.8,
                           time_interval=1,
                           dsegcodes: List[str] = [],
                           ):
        """Add OV Kenngrößen-Matrizen für Zeitscheiben"""
        time_series = params.time_series

        self.set_category('OV_TimeSeries_Skims')
        for idx, ts in time_series.iterrows():
            ts_code = ts.code
            ts_name = ts.name_long
            fromtime = self.get_timestring(ts.from_hour)
            totime = self.get_timestring(ts.to_hour)

            for dsegcode in dsegcodes:
                self.add_daten_matrix(
                    code='FAR',
                    matrixtype='Skim',
                    name=f'Fahrpreis {dsegcode} {ts_name}',
                    filename=f'FAR_{ts_code}',
                    dsegcode=dsegcode,
                    day=1,
                    fromtime=fromtime,
                    totime=totime,
                    initmatrix=1,
                    timeref='Departuretime',
                    # modecode='O',
                )

            dsegcode = 'O'

            self.add_daten_matrix(
                code='PJT',
                matrixtype='Skim',
                name=f'Empfundene Reisezeit {dsegcode} {ts_name}',
                filename=f'PJT_{ts_code}',
                dsegcode=dsegcode,
                day=1,
                fromtime=fromtime,
                totime=totime,
                timeref='Departuretime',
                initmatrix=1,
                # modecode='O'
            )

            self.add_daten_matrix(
                code='JRD',
                matrixtype='Skim',
                name=f'Reiseweite {dsegcode} {ts_name}',
                filename=f'JRD_{ts_code}',
                dsegcode=dsegcode,
                day=1,
                fromtime=fromtime,
                totime=totime,
                initmatrix=1,
                timeref='Departuretime',
                # modecode='O',
            )
            self.add_daten_matrix(
                code='FFZ',
                matrixtype='Skim',
                name=f'Fahrzeugfolgezeit {dsegcode} {ts_name}',
                filename=f'FFZ_{ts_code}',
                dsegcode=dsegcode,
                day=1,
                fromtime=fromtime,
                totime=totime,
                initmatrix=1,
                timeref='Departuretime',
                # modecode='O',
            )

        for dsegcode in dsegcodes:
            self.add_daten_matrix(
                code='FAR',
                matrixtype='Skim',
                name=f'Fahrpreis {dsegcode}',
                dsegcode=dsegcode,
                fromtime='',
                totime='',
                timeref='Departuretime',
                # moduscode='O',
            )

        dsegcode = 'O'

        self.add_daten_matrix(
            code='PJT',
            matrixtype='Skim',
            name=f'Empfundene Reisezeit {dsegcode}',
            dsegcode=dsegcode,
            fromtime='',
            totime='',
            timeref='Departuretime',
            #modecodee='O',
        )
        self.add_daten_matrix(
            code='FFZ',
            matrixtype='Skim',
            name=f'Fahrzeugfolgezeit {dsegcode}',
            dsegcode=dsegcode,
            fromtime='',
            totime='',
            timeref='Departuretime',
            # moduscode='O',
        )
        self.add_daten_matrix(
            code='XADT',
            matrixtype='Skim',
            name=f'Erweiterte Anpassungszeit {dsegcode}',
            dsegcode=dsegcode,
            fromtime='',
            totime='',
            timeref='Departuretime',
            modecode='O',
        )
        self.add_daten_matrix(
            code='JRD',
            matrixtype='Skim',
            name=f'Reiseweite {dsegcode}',
            dsegcode=dsegcode,
            fromtime='',
            totime='',
            # initmatrix=1,
            timeref='Departuretime',
            modecode='O',
        )

        self.set_category('OV_TimeSeries_Skims_Formula')

        self.add_daten_matrix(
            code='No_Connection_Forward',
            matrixtype='Skim',
            name='Keine ÖV-Verbindung in Zeitscheibe Hinweg',
            dsegcode=dsegcode,
          modecode='O',
        )
        self.add_daten_matrix(
            code='No_Connection_Backward',
            matrixtype='Skim',
            name='Keine ÖV-Verbindung in Zeitscheibe Rückweg',
            dsegcode=dsegcode,
          modecode='O',
        )
        # ÖV-Kosten
        self.set_category('OV_Skims_Fare')
        ticketarten = ['Singleticket',
                       'MonatskarteAbo',
                       ]
        for ticketart in ticketarten:
            self.add_daten_matrix(
                code=ticketart,
                matrixtype='Skim',
              modecode='O',
                loadmatrix=0,
                savematrix=savematrix,
            )

        self.add_daten_matrix(
            code='OVDIS',
            matrixtype='Skim',
            name='OV Reiseweite',
            filename='OVDIS',
            dsegcode=dsegcode,
            loadmatrix=0,
            savematrix=savematrix,
          modecode='O',
        )

        userdef.add_data_attribute('Network', 'DistanceKorrBisKm_OV',
                                    defaultvalue=3)
        userdef.add_data_attribute('Network', 'DistanceKorrFaktor_OV',
                                    defaultvalue=-1.5)

        self.add_formel_matrix(
            code='DistanzKorrektur_OV',
            matrixtype='Skim',
            name='DistanzKorrektur_OV',
            filename='DistanzKorrektur_OV',
          modecode='O',
            formula='(Matrix([CODE] = "KM") < [DistanceKorrBisKm_OV]) *'
            ' [DistanceKorrFaktor_OV] * '
            '([DistanceKorrBisKm_OV] - Matrix([CODE] = "KM"))',
        )

        # ÖV-Nachfragematrizen nach Zeitscheiben
        self.set_category('OV_TimeSeries_Skims_Formula')

        # PJT_All-Matrix für nur eine Zeitscheibe
        ts = time_series.loc[time_interval]
        ts_code = ts['code']
        fromtime= self.get_time_seconds(ts['from_hour'])
        totime = self.get_time_seconds(ts['to_hour'])
        formula = (
            f'Matrix([CODE] = "PJT" & [DSEGCODE]="{dsegcode}" & [FROMTIME]={fromtime} & [TOTIME]={totime}) + '
            f'{factor} * POW('
            f'Matrix([CODE] = "FFZ" & [FROMTIME]={fromtime} & [TOTIME]={totime})'
            f', {exponent})')

        complete_formula = f'(({formula}) + TRANSPOSE({formula})) * 0.5'

        self.add_formel_matrix(
            code='PJT_All',
            matrixtype='Skim',
            name='Empfundene Reisezeit alle Aktivitäten',
            dsegcode=dsegcode,
            formula=complete_formula,
        )

    def add_iv_kg_matrices(self,
                           userdef: UserDefinedAttribute,
                           savematrix=0):
        """Add PrT Skim Matrices"""
        self.set_category('IV_Skims')
        self.add_daten_matrix(code='DIS',
                              name=f'Fahrweite Rad (R)',
                              loadmatrix=0,
                              matrixtype='Skim',
                              dsegcode='R',
                              fromtime='',
                              totime='',
                              savematrix=savematrix)
        self.add_daten_matrix(code='IMP',
                              name=f'Widerstand Rad (R)',
                              loadmatrix=0,
                              matrixtype='Skim',
                              dsegcode='R',
                              fromtime='',
                              totime='',
                              savematrix=savematrix)
        for dsegcode in ['P', 'PG']:
            self.add_daten_matrix(code='DIS',
                                  name=f'Fahrweite Pkw ({dsegcode})',
                                  matrixtype='Skim',
                                  dsegcode=dsegcode,
                                  fromtime='',
                                  totime='',
                                  savematrix=savematrix)
            self.add_daten_matrix(code='TT0',
                                  name=f't0 Pkw ({dsegcode})',
                                  matrixtype='Skim',
                                  dsegcode=dsegcode,
                                  fromtime='',
                                  totime='',
                                  savematrix=savematrix)
            self.add_daten_matrix(code='TTC',
                                  name=f'tAkt Pkw ({dsegcode})',
                                  matrixtype='Skim',
                                  dsegcode=dsegcode,
                                  fromtime='',
                                  totime='',
                                  savematrix=savematrix)

        self.add_daten_matrix(code='TFUSS', name='tFuss',
                              matrixtype='Skim',
                              dsegcode='F',
                            modecode='F',
                              savematrix=savematrix)
        self.add_daten_matrix(code='TRAD', name='tRad',
                              matrixtype='Skim',
                              dsegcode='R',
                            modecode='R',
                              savematrix=savematrix)
        self.add_daten_matrix(code='TTC_boxcox',
                              name='tAkt Pkw BoxCox-Transformiert',
                              matrixtype='Skim',
                              dsegcode='P',
                            modecode='P',
                              savematrix=savematrix)

        self.add_daten_matrix(code='TOL',
                              name='Maut PG',
                              matrixtype='Skim',
                              dsegcode='PG',
                            modecode='P',
                              savematrix=savematrix)

        userdef.add_formula_attribute(
            objid='Bezirk',
            name='Binnendistanz_area',
            formula='SQRT([FLAECHEKM2]) / 3',
            comment='geschätzte Binnendistanz in km',
        )

        self.add_formel_matrix(
            code='PkwKosten',
            matrixtype='Skim',
            dsegcode='P',
            name='Pkw Fahrtkosten',
            formula='Matrix([CODE] = "DIS" & [DSEGCODE] = "PG") * '
                   '[COST_PER_KM_PKW]'
                   ' + Matrix([CODE] = "TOL" & [DSEGCODE] = "PG")')

        self.add_formel_matrix(code='SFUSS', name='sFuss',
                               matrixtype='Skim',
                               dsegcode='F',
                             modecode='F',
                               formula='Matrix([CODE] = "TFUSS") * 4.5 / 60')

        # Reiseweite
        formula = ('Matrix([CODE] = "DIS" & [DSEGCODE] = "PG")')
        #formula = ('Min (Matrix([CODE] = "DIS" & [DSEGCODE] = "PG") : '
                  #'Matrix([CODE] = "DIS" & [DSEGCODE] = "R"))')

        self.add_formel_matrix(code='KM', name='Reiseweite',
                               matrixtype='Skim',
                               formula=formula)

        userdef.add_data_attribute('Network', 'DistanceKorrBisKm_Pkw',
                                    defaultvalue=1.2)
        userdef.add_data_attribute('Network', 'DistanceKorrFaktor_Pkw',
                                    defaultvalue=-4)

        self.add_formel_matrix(
            code='DistanzKorrektur_Pkw',
            matrixtype='Skim',
            name='DistanzKorrektur_Pkw',
            filename='DistanzKorrektur_Pkw',
          modecode='P',
            formula='(Matrix([CODE] = "KM") < [DistanceKorrBisKm_Pkw]) *'
            ' [DistanceKorrFaktor_Pkw] * '
            '([DistanceKorrBisKm_Pkw] - Matrix([CODE] = "KM"))',
        )
        self.add_daten_matrix(code='UDS', name='Benutzerdefiniert PG',
                              matrixtype='Skim',
                              dsegcode='PG')

    def add_iv_demand(self, savematrix=0, loadmatrix=1):
        """Add PrT Demand Matrices"""

        self.set_category('Visem_Demand')
        self.add_daten_matrix(code='Visem_P', name='Pkw regional',
                              loadmatrix=loadmatrix,
                              matrixtype='Demand',
                              dsegcode='P',
                            modecode='P',
                              savematrix=savematrix,
                              obb_matrix_ref='[CODE]="Visem_OBB_P"',
                              matrixfolder='Analysefall',
                              )

        self.set_category('Other_Demand')

        self.add_daten_matrix(code='Pkw_Wirtschaftsverkehr',
                              name='Pkw-Wirtschaftsverkehr',
                              loadmatrix=loadmatrix,
                              matrixfolder='Wiver',
                              matrixtype='Demand',
                              dsegcode='P_W',
                            modecode='P_W')
        self.add_daten_matrix(code='Lieferfahrzeuge', name='Lieferfahrzeuge',
                              loadmatrix=loadmatrix,
                              matrixfolder='Wiver',
                              matrixtype='Demand',
                              dsegcode='LKW_S',
                            modecode='LKW_S')
        self.add_daten_matrix(code='Lkw_bis_12to',
                              name='Lkw zw. 3,5 und 12 to',
                              matrixfolder='Wiver',
                              loadmatrix=loadmatrix,
                              matrixtype='Demand',
                              dsegcode='LKW_L',
                            modecode='LKW_L')
        self.add_daten_matrix(code='Lkw_über_12to', name='Lkw > 3,5 to',
                              loadmatrix=loadmatrix,
                              matrixfolder='Wiver',
                              matrixtype='Demand',
                              dsegcode='LKW_XL',
                            modecode='LKW_XL')
        self.add_daten_matrix(code='FernverkehrPkw',
                              name='Pkw-Fernverkehr',
                              loadmatrix=loadmatrix,
                              matrixtype='Demand',
                              dsegcode='P_ex',
                            modecode='P_ex',
                              matrixfolder='Fernverkehr')
        self.add_daten_matrix(code='FernverkehrLkw',
                              name='Lkw-Fernverkehr',
                              loadmatrix=loadmatrix,
                              matrixtype='Demand',
                              dsegcode='Lkw_ex',
                            modecode='Lkw_ex',
                              matrixfolder='Fernverkehr')

        ## Summen Schwerverkehr und Kfz bis 3.5 to
        nsegs = ['Lkw_bis_12to',
                 'Lkw_über_12to',
                 'FernverkehrLkw']
        formula = ' + '.join((f'Matrix([CODE]="{nseg}" & [OBJECTTYPEREF]=2)'
                            for nseg in nsegs))
        self.add_formel_matrix(code='Schwerverkehr',
                               formula=formula,
                               name='Schwerverkehr ohne Busse',
                               matrixtype='Demand',
                               dsegcode='SV')

        nsegs = ['Visem_P',
                 'Pkw_Wirtschaftsverkehr',
                 'Lieferfahrzeuge',
                 'FernverkehrPkw',
                 ]
        formula = ' + '.join((f'Matrix([CODE]="{nseg}" & [OBJECTTYPEREF]=2)'
                             for nseg in nsegs))
        self.add_formel_matrix(code='Kfz_35',
                               formula=formula,
                               name='Kfz bis 3,5 to',
                               matrixtype='Demand',
                               dsegcode='PG',
                             modecode='P')

    def add_ov_demand(self, savematrix=0, loadmatrix=1):
        """Add PrT Demand Matrices"""
        self.set_category('Visem_Demand')
        self.add_daten_matrix(code='Visem_O', name='ÖPNV',
                              matrixtype='Demand',
                              dsegcode='O',
                            modecode='O',
                              savematrix=savematrix,
                              obb_matrix_ref='[CODE]="Visem_OBB_O"',
                              matrixfolder='Analysefall',
                              )
        self.set_category('OV_Demand')
        self.add_daten_matrix(code='FernverkehrBahn', name='Fernverkehr Bahn',
                              loadmatrix=loadmatrix,
                              matrixtype='Demand',
                              dsegcode='O_ex',
                            modecode='O',
                              matrixfolder='Fernverkehr')

    def add_other_demand_matrices(self,
                                  params: Params,
                                  loadmatrix=1,
                                  savematrix=0):
        """Add Demand Matrices for other modes"""
        self.set_category('Visem_Demand')
        existing_codes = self.df['CODE'].tolist()

        matcode = 'Visem_Gesamt'
        matcode_obb = 'Visem_OBB_Gesamt'
        self.add_daten_matrix(code=matcode,
                              name='Gesamtwege Visem Region',
                              loadmatrix=loadmatrix,
                              savematrix=savematrix,
                              matrixtype='Demand',
                              obb_matrix_ref=f'[CODE]="{matcode_obb}"')
        self.add_daten_matrix(code=matcode_obb,
                              name='Gesamtwege Visem Region',
                              loadmatrix=loadmatrix,
                              savematrix=savematrix,
                              matrixtype='Demand',
                              objecttyperef='Mainzone')

        for m, mode in params.modes.iterrows():
            code = mode['code']
            mode_name = mode['name']
            matname = f'Wege {mode_name}'
            matcode = f'Visem_{code}'
            if matcode in existing_codes:
                continue
            self.add_daten_matrix(code=matcode,
                                  name=matname,
                                  loadmatrix=loadmatrix,
                                  matrixtype='Demand',
                                modecode=code,
                                  dsegcode=code,
                                  savematrix=savematrix,
                                  obb_matrix_ref=f'[CODE]="Visem_OBB_{code}"',
                                  )

        for m, mode in params.modes.iterrows():
            code = mode['code']
            matcode = f'Visem_OBB_{code}'
            mode_name = mode['bezeichnung']
            name = f'Wege {mode_name} Oberbezirk Region'
            if matcode in existing_codes:
                continue
            self.add_daten_matrix(code=matcode,
                                  name=name,
                                  loadmatrix=loadmatrix,
                                  matrixtype='Demand',
                                  moduscode=code,
                                  objecttyperef='Mainzone')

        # ÖV-Fahrten Schüler für Standi
        code_sch = 'Visem_O_Schueler'
        matcode_obb = 'Visem_OBB_OV_Schueler'

        self.add_daten_matrix(code=code_sch,
                              name=code_sch,
                              loadmatrix=loadmatrix,
                              savematrix=savematrix,
                              matrixtype='Demand',
                              obb_matrix_ref=f'[CODE]="{matcode_obb}"')

        self.add_daten_matrix(code=matcode_obb,
                              name=matcode_obb,
                              loadmatrix=loadmatrix,
                              savematrix=savematrix,
                              matrixtype='Demand',
                              objecttyperef='Mainzone')

        code = 'Visem_O_Erwachsene'
        matcode_obb = 'Visem_OBB_OV_Erwachsene'

        self.add_formel_matrix(code=code,
                               name=code,
                               matrixtype='Demand',
                               formula=f'Matrix([CODE]="Visem_O") - Matrix([CODE]="{code_sch}")',
                               obb_matrix_ref=f'[CODE]="{matcode_obb}"')

        self.add_daten_matrix(code=matcode_obb,
                              name=matcode_obb,
                              matrixtype='Demand',
                              objecttyperef='Mainzone')

        # Verkehrsleistung
        self.set_category('Demand_Verkehrsleistung')
        for m, mode in params.modes.iterrows():
            distance_matrix = mode['distance_matrix']
            code = mode['code']
            matcode = f'VL_{code}'
            mode_name = mode['name']
            matname = f'Verkehrsleistung {mode_name}'
            dsegcode = mode['default_nsegcode']
            if dsegcode:
                cond_nsegcode = f' & [DSEGCODE] = "{dsegcode}"'
            else:
                cond_nsegcode = ''
            if matcode in existing_codes:
                continue
            formula = f'Matrix([CODE]="Visem_{code}") * '\
                f'Matrix([CODE]="{distance_matrix}"{cond_nsegcode})'
            matcode_obb = f'VL_OBB_{code}'
            self.add_formel_matrix(code=matcode,
                                   name=matname,
                                   formula=formula,
                                   matrixtype='Demand',
                                modecodeode=code,
                                   obb_matrix_ref=f'[CODE]="{matcode_obb}"',
                                   )
            self.add_daten_matrix(code=matcode_obb,
                                  name=name,
                                  loadmatrix=0,
                                  matrixtype='Demand',
                               modecodeode=code,
                                  objecttyperef='Mainzone')

        # Verkehrsleistung Standi
        mode_code = 'O'
        mode = params.modes.loc[params.modes['code'] == mode_code].iloc[0]
        distance_matrix = mode['distance_matrix']
        for code in ['Schueler', 'Erwachsene']:
            matcode = f'VL_{mode_code}_{code}'

            formula = f'Matrix([CODE]="Visem_{mode_code}_{code}") * '\
                f'Matrix([CODE]="{distance_matrix}")'
            matcode_obb = f'VL_OBB_{mode_code}_{code}'
            self.add_formel_matrix(code=matcode,
                                   name=matcode,
                                   formula=formula,
                                   matrixtype='Demand',
                                modecodeode=mode_code,
                                   obb_matrix_ref=f'[CODE]="{matcode_obb}"',
                                   )
            self.add_daten_matrix(code=matcode_obb,
                                  name=name,
                                  loadmatrix=0,
                                  matrixtype='Demand',
                                  moduscode=mode_code,
                                  objecttyperef='Mainzone')

    def add_ov_haupt_ap_demand_matrices(self,
                                        ds_tagesgang: xr.Dataset,
                                        loadmatrix=0,
                                        savematrix=1):
        """Add Demand Matrices for other modes"""
        self.set_category('Demand_OV_Tagesgang')
        for hap in ds_tagesgang.hap:
            matcode = f'Visem_OV_{hap.lab_hap.values}'
            self.add_daten_matrix(code=matcode,
                                  loadmatrix=loadmatrix,
                                  matrixtype='Demand',
                              modecodecode='O',
                                  savematrix=savematrix,
                                  )

    def add_commuter_matrices(self,
                              loadmatrix=1,
                              savematrix=1):
        """Add Commuter Matrices"""
        self.set_category('Commuters')
        self.add_daten_matrix(code='Pendlermatrix',
                              name='Pendlermatrix der BA disaggregiert auf Bezirke',
                              loadmatrix=0,
                              matrixtype='Demand',
                              matrixfolder='Pendler')
        self.add_daten_matrix(code='Pendlermatrix_OBB',
                              name='Pendlermatrix der BA (SvB)',
                              objecttyperef='Mainzone',
                              matrixtype='Demand',
                              loadmatrix=1,
                              matrixfolder='Pendler')
        self.add_daten_matrix(code='Pendlerkorrektur',
                              name='Pendlerkorrektur auf Bezirksebene',
                              objecttyperef='Zone',
                              matrixtype='Demand',
                              loadmatrix=1,
                              matrixfolder='Pendler')
        formula = 'Matrix([CODE]="Pendlermatrix_OBB") * [SUM:PGRUPPEN\ERWERBSTAETIGE] '\
            '/ MATRIXSUM(Matrix([CODE] = "Pendlermatrix_OBB"))'
        self.add_daten_matrix(
            code='Pendlermatrix_OBB_Gesamt',
            name='Pendlermatrix_OBB incl Nicht-SVB-Beschäftigte',
            matrixtype='Demand',
            objecttyperef='Mainzone',
            matrixfolder='Pendler',
            savematrix=0,
        )

        self.set_category('DestinationChoiceSkims')
        self.add_formel_matrix(
            code='Aussen2Aussen',
            matrixtype='Skim',
            formula='-999999 * (FROM[MODELLIERUNGSRAUM] = 0) * (TO[MODELLIERUNGSRAUM] = 0)')
        self.add_formel_matrix(
            code='Innen2Aussen',
            matrixtype='Skim',
            formula='-999999 * ((FROM[MODELLIERUNGSRAUM] = 1) * (TO[MODELLIERUNGSRAUM] =1) + (FROM[MODELLIERUNGSRAUM] = 0) * (TO[MODELLIERUNGSRAUM] = 0))')

    def add_logsum_matrices(self,
                            demand_strata: 'Nachfrageschicht',
                            actchains: 'Activitychain',
                            matrix_range='Logsums',
                            ):
        """Add logsum matrices for each person group and main activity"""

        self.set_category(matrix_range)
        ketten = {ac_code: act['ACTIVITYCODES'].split(',')[1: -1]
                  for ac_code, act
                  in actchains.df.iterrows()}  # type: Mapping[str, List[str]]
        pgr_activities = defaultdict(set)  # type: Mapping[Tuple[str, str], set]
        for ds_code, ds in demand_strata.df.iterrows():
            pgr = ds['PGRUPPENCODES']
            demandmodelcode = ds['DEMANDMODELCODE']
            if demandmodelcode in ('VisemGGR', 'Pendler'):
                activities = pgr_activities[(demandmodelcode, pgr)]
                new_activities = ketten[ds['AKTKETTENCODE']]
                for activity in new_activities:
                    activities.add(activity)
        for (nmc, pgr), activities in pgr_activities.items():
            for activity in activities:
                code = 'LogsumMatrix'
                name = f'Logsum {pgr} {activity}'
                self.add_daten_matrix(
                    code,
                    name,
                    matrixtype='Skim',
                    loadmatrix=0,
                    savematrix=0,
                    initmatrix=1,
                    nachfrmodellcode=nmc,
                    persongroupcode=pgr,
                    activitycode=activity,
                )
