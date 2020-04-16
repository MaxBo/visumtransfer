# -*- coding: utf-8 -*-

import datetime
from collections import defaultdict
import xarray as xr
from visumtransfer.params import Params
from typing import Mapping
from .basis import BenutzerdefiniertesAttribut
from visumtransfer.visum_table import (VisumTable)


class MatrixCategories(dict):
    _end_block: Mapping[str, int] = {
        'Visem_Demand': 20,
        'Visem_OV_Stunden': 30,
        'Other_Demand': 90,
        'OV_Demand': 100,
        'DestinationChoiceSkims': 110,
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
        'VL_Activities_OBB': 1600,
        'Activities_OBB': 1700,
        'OV_TimeSeries_Skims_Formula': 1800,
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
        self['_fallback'] = iter(range(start_idx, 9999999))


class Matrix(VisumTable):
    name = 'Matrizen'
    code = 'MATRIX'
    matrix_category = ''

    _cols = ('NR;CODE;NAME;MATRIXTYP;BEZUGSTYP;NSEGCODE;NSCHICHTSET;DATNAME;'
    'ANZDEZSTELLEN;DATENQUELLENTYP;FORMEL;TAG;VONZEIT;BISZEIT;ZEITBEZUG;'
    'MODUSCODE;MODUSSET;PERSONENGRUPPENSET;PGRUPPENCODE;AKTIVCODE;'
    'QUELLAKTIVITAETSET;ZIELAKTIVITAETSET;'
    'INITMATRIX;SAVEMATRIX;LOADMATRIX;MATRIXFOLDER;'
    'CALIBRATIONCODE;NACHFRMODELLCODE;CATEGORY')

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

    def set_category(self, matrix_category: str):
        """Set set matrix_category"""
        self.matrix_category = matrix_category

    @property
    def matrix_numbers(self) -> MatrixCategories:
        return self._number_block[self.matrix_category]

    def next_number(self) -> int:
        """Return next matrix number in range"""
        try:
            nr = next(self.matrix_numbers)
        except StopIteration:
            nr = next(self._number_block['_fallback'])
        return nr

    def add_daten_matrix(self,
                         code: str,
                         name='',
                         loadmatrix=0,
                         matrixfolder='',
                         datname='',
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
        datname : str, optional
            the filename of the matrix on disk.
            If not provided, the code is taken as name
        category : str, optional
            the matrix category. If not given,
            use the category last set by set_category()

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
                       category=category or self.matrix_category,
                       ** kwargs)
        self.add_row(row)
        return nr

    def add_formel_matrix(self,
                          code: str,
                          formel: str,
                          name='',
                          datname='',
                          category: str = None,
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
        category : str, optional
            the matrix category. If not given,
            use the category last set by set_category()
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
                       category=category or self.matrix_category,
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
        nsegcode = 'A'
        self.set_category('OV_TimeSeries_Skims')
        for idx, ts in time_series.iterrows():
            ts_code = ts.code
            vonzeit = self.get_timestring(ts.from_hour)
            biszeit = self.get_timestring(ts.to_hour)
            self.add_daten_matrix(
                code='PJT',
                matrixtyp='Kenngröße',
                name=f'Empfundene Reisezeit {nsegcode}',
                datname=f'PJT_{ts_code}',
                nsegcode=nsegcode,
                tag=1,
                vonzeit=vonzeit,
                biszeit=biszeit,
                zeitbezug='Abfahrtszeit',
                initmatrix=1,
                # moduscode='O'
            )
            self.add_daten_matrix(
                code='FAR',
                matrixtyp='Kenngröße',
                name=f'Fahrpreis {nsegcode}',
                datname=f'FAR_{ts_code}',
                nsegcode=nsegcode,
                tag=1,
                vonzeit=vonzeit,
                biszeit=biszeit,
                initmatrix=1,
                zeitbezug='Abfahrtszeit',
                # moduscode='O',
            )
            self.add_daten_matrix(
                code='XADT',
                matrixtyp='Kenngröße',
                name=f'Erweiterte Anpassungszeit {nsegcode}',
                datname=f'XADT_{ts_code}',
                nsegcode=nsegcode,
                tag=1,
                vonzeit=vonzeit,
                biszeit=biszeit,
                initmatrix=1,
                zeitbezug='Abfahrtszeit',
                # moduscode='O',
            )
            self.add_daten_matrix(
                code='JRD',
                matrixtyp='Kenngröße',
                name=f'Reiseweite {nsegcode}',
                datname=f'JRD_{ts_code}',
                nsegcode=nsegcode,
                tag=1,
                vonzeit=vonzeit,
                biszeit=biszeit,
                initmatrix=1,
                zeitbezug='Abfahrtszeit',
                # moduscode='O',
            )

        self.add_daten_matrix(
            code='PJT',
            matrixtyp='Kenngröße',
            name=f'Empfundene Reisezeit {nsegcode}',
            nsegcode=nsegcode,
            vonzeit='',
            biszeit='',
            zeitbezug='Abfahrtszeit',
            # moduscode='O',
        )
        self.add_daten_matrix(
            code='FAR',
            matrixtyp='Kenngröße',
            name=f'Fahrpreis {nsegcode}',
            nsegcode=nsegcode,
            vonzeit='',
            biszeit='',
            zeitbezug='Abfahrtszeit',
            # moduscode='O',
        )
        self.add_daten_matrix(
            code='XADT',
            matrixtyp='Kenngröße',
            name=f'Erweiterte Anpassungszeit {nsegcode}',
            nsegcode=nsegcode,
            vonzeit='',
            biszeit='',
            zeitbezug='Abfahrtszeit',
            # moduscode='O',
        )

        self.set_category('OV_TimeSeries_Skims_Formula')

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
        self.set_category('OV_Skims_Fare')
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
            name=f'Reiseweite {nsegcode}',
            nsegcode=nsegcode,
            vonzeit='',
            biszeit='',
            # initmatrix=1,
            zeitbezug='Abfahrtszeit',
            # moduscode='O',
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
        self.set_category('OV_TimeSeries_Skims_Formula')

        # PJT_All-Matrix für nur eine Zeitscheibe
        ts = time_series.loc[time_interval]
        ts_code = ts['code']
        vonzeit = self.get_time_seconds(ts['from_hour'])
        biszeit = self.get_time_seconds(ts['to_hour'])
        formula = (
            f'Matrix([CODE] = "PJT" & [FROMTIME]={vonzeit} & [TOTIME]={biszeit}) + '
            f'{factor} * POW('
            f'(Matrix([CODE] = "XADT" & [FROMTIME]={vonzeit} & [TOTIME]={biszeit}) * 4 + 1)'
            f', {exponent})')

        complete_formula = f'(({formula}) + TRANSPOSE({formula})) * 0.5'

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
        self.set_category('IV_Skims')
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
        mode_lkw = 'X'

        self.set_category('Visem_Demand')
        self.add_daten_matrix(code='Visem_P', name='Pkw regional',
                              loadmatrix=loadmatrix,
                              matrixtyp='Nachfrage',
                              nsegcode='P',
                              moduscode='P',
                              savematrix=savematrix)

        self.set_category('Other_Demand')
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
                              moduscode=mode_lkw)
        self.add_daten_matrix(code='Lkw_über_12to', name='Lkw > 3,5 to',
                              loadmatrix=loadmatrix,
                              matrixtyp='Nachfrage',
                              nsegcode='B_L2',
                              moduscode=mode_lkw)
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
                              moduscode=mode_lkw)

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
                               moduscode=mode_lkw)

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
                               nsegcode='PG',
                               moduscode='P')

    def add_ov_demand(self, savematrix=0, loadmatrix=1):
        """Add PrT Demand Matrices"""
        self.set_category('Visem_Demand')
        self.add_daten_matrix(code='Visem_O', name='ÖPNV',
                              loadmatrix=loadmatrix,
                              matrixtyp='Nachfrage',
                              nsegcode='A',
                              moduscode='O',
                              savematrix=savematrix)
        self.set_category('OV_Demand')
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
        self.set_category('Visem_Demand')
        existing_codes = self.df['CODE']

        self.add_daten_matrix(code='Visem_Gesamt',
                              name='Gesamtwege Visem Region',
                              loadmatrix=loadmatrix,
                              savematrix=savematrix,
                              matrixtyp='Nachfrage')

        for m, mode in params.modes.iterrows():
            code = mode['code']
            mode_name = mode['name']
            matname = f'Wege {mode_name}'
            matcode = f'Visem_{code}'
            if matcode not in existing_codes:
                self.add_daten_matrix(code=matcode,
                                      name=matname,
                                      loadmatrix=loadmatrix,
                                      matrixtyp='Nachfrage',
                                      moduscode=code,
                                      savematrix=savematrix,
                                      )


        for m, mode in params.modes.iterrows():
            code = mode['code']
            matcode = 'Demand_{}_OBB'.format(code)
            mode_name = mode['name']
            name = f'Fahrten {mode_name} Regionsbewohner Oberbezirk'
            if matcode not in existing_codes:
                self.add_daten_matrix(code=matcode,
                                      name=name,
                                      loadmatrix=loadmatrix,
                                      matrixtyp='Nachfrage',
                                      moduscode=code,
                                      bezugstyp='Oberbezirk')

        self.set_category('Demand_Verkehrsleistung')
        for m, mode in params.modes.iterrows():
            distance_matrix = mode['distance_matrix']
            code = mode['code']
            matcode = f'VL_{code}'
            mode_name = mode['name']
            matname = f'Verkehrsleistung {mode_name}'
            if matcode not in existing_codes:
                formel = f'Matrix([CODE]="Visem_{code}") * '\
                    f'Matrix([CODE]="{distance_matrix}")'
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
        self.set_category('Demand_OV_Tagesgang')
        for hap in ds_tagesgang.hap:
            matcode = f'Visem_OV_{hap.lab_hap.values}'
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
        self.set_category('Commuters')
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

        self.set_category('DestinationChoiceSkims')
        self.add_formel_matrix(
            code='Aussen2Aussen',
            matrixtyp='Kenngröße',
            formel='-999999 * (FROM[TYPNR] > 3) * (TO[TYPNR] > 3)')
        self.add_formel_matrix(
            code='Innen2Aussen',
            matrixtyp='Kenngröße',
            formel='-999999 * ((FROM[TYPNR] <= 3) * (TO[TYPNR] <= 3) + (FROM[TYPNR] > 3) * (TO[TYPNR] > 3))')

    def add_logsum_matrices(self,
                            demand_strata: 'Nachfrageschicht',
                            actchains: 'Aktivitaetenkette',
                            matrix_range='Logsums',
                            ):
        """Add logsum matrices for each person group and main activity"""

        self.set_category(matrix_range)
        ketten = {ac_code: act['AKTIVCODES'].split(',')[1: -1]
                  for ac_code, act
                  in actchains.df.iterrows()}  # type: Mapping[str, List[str]]
        pgr_activities = defaultdict(set)  # type: Mapping[Tuple[str, str], set]
        for ds_code, ds in demand_strata.df.iterrows():
            pgr = ds['PGRUPPENCODES']
            nachfragemodellcode = ds['NACHFRAGEMODELLCODE']
            if nachfragemodellcode in ('VisemT', 'Pendler'):
                activities = pgr_activities[(nachfragemodellcode, pgr)]
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
                    matrixtyp='Kenngröße',
                    loadmatrix=0,
                    savematrix=0,
                    initmatrix=1,
                    nachfrmodellcode=nmc,
                    pgruppencode=pgr,
                    aktivcode=activity,
                    )
