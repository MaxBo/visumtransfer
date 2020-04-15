# -*- coding: utf-8 -*-

import numpy as np
import pandas as pd
import warnings
from collections import defaultdict
from .matrizen import Matrix
from .basis import BenutzerdefiniertesAttribut
from visumtransfer.visum_table import (VisumTable)
from visumtransfer.params import Params



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
        self.gd_codes = defaultdict(list)

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
        self.set_df_from_table()

    def create_groups_generation(self, params: Params):
        # sort person group by code
        person_groups = params.gg
        for p in person_groups:
            self.add_group_generation(code=p['code'],
                                      name=p['code'],
                                      groupdestmode=p['group_dest_mode'])

    def create_groups_destmode(self,
                               params: Params,
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

    def create_groups_rsa(self,
                          person_groups: np.recarray,
                          trip_chain_rates: np.recarray,
                          model_code: str = 'VisemRSA'):
        """"""
        tcr = pd.DataFrame(trip_chain_rates)
        for g, gdd in enumerate(person_groups):
            gd_code = gdd['code']
            name = gdd['name']
            self.add_group(
                code=gd_code,
                name=name,
                modellcode=model_code,
                car_availability=gdd['car_availability'],
                occupation=gdd['occupation'],
                groupdestmode=gd_code,
            )
            tc_group = tcr.loc[tcr.group == gd_code]
            for idx, tc in tc_group.iterrows():
                self.gd_codes[gd_code].append(tc.code)
        self.create_table()

    def add_calibration_matrices_and_attributes(
          self,
          params: Params,
          matrices: Matrix,
          userdefined: BenutzerdefiniertesAttribut):
        """
        Add Output Matrices for PersonGroups
        """
        matrices.set_category('Demand_Pgr')
        calibration_defs = ['occupation', 'car_availability']
        modes = params.mode_set.split(',')
        for cg in calibration_defs:
            calibration_groups = np.unique(self.table[cg.upper()])
            for group in calibration_groups:
                if group:
                    gr_code = f'{cg}_{group}'
                    for mode in modes:
                        # add output matrix
                        str_name = f'Wege mit Verkehrsmittel {mode} der Gruppe {gr_code}'
                        matrices.add_daten_matrix(
                            code=f'{gr_code}_{mode}',
                            name=str_name,
                            moduscode=mode,
                            calibrationcode=gr_code)

                    # Alternativenspezifische Konstante im Modell
                    userdefined.add_daten_attribute(
                        objid='MODUS',
                        name=f'Const_{gr_code}')

                    # Wege nach Modus und Modal Split der Gruppe
                    formel = f'TableLookup(MATRIX Mat: Mat[CODE]="{gr_code}_"+[CODE]: Mat[SUMME])'
                    userdefined.add_formel_attribute(
                        objid='MODUS',
                        name=f'Trips_{gr_code}',
                        formel=formel,
                        kommentar=f'Gesamtzahl der Wege der Gruppe {gr_code}',
                    )
                    # Wege Gesamt der Gruppe
                    userdefined.add_formel_attribute(
                        objid='NETZ',
                        name=f'Trips_{gr_code}',
                        formel=f'[SUM:MODI\Trips_{gr_code}]',
                        kommentar=f'Gesamtzahl der Wege der Gruppe {gr_code}',
                    )
                    # Modal Split der Gruppe
                    userdefined.add_formel_attribute(
                        objid='MODUS',
                        name=f'MS_{gr_code}',
                        formel=f'[Trips_{gr_code}] / [NETZ\Trips_{gr_code}]',
                        kommentar=f'Modal Split der Gruppe {gr_code}',
                    )

                    # Ziel-Modal Split der Gruppe
                    userdefined.add_daten_attribute(
                        objid='Modus',
                        name=f'Target_MS_{gr_code}',
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
                      activities: np.recarray,
                      model: str,
                      suffix=''):
        rows = []
        for a in activities:
            # Heimataktivität hat keine Strukturgröße
            if not a['potential']:
                continue
            row = self.Row(nachfragemodellcode=model)
            row.code = a['potential'] + suffix
            row.name = a['name']
            rows.append(row)
        self.add_rows(rows)


class Strukturgroessenwert(VisumTable):
    name = 'Strukturgrößenwerte'
    code = 'STRUKTURGROESSENWERT'
    _cols = 'BEZNR;STRUKTURGROESSENCODE;WERT'
    _longformat = True


class PersonengruppeJeBezirk(VisumTable):
    name = 'Personengruppe je Bezirk'
    code = 'PERSONENGRUPPEJEBEZIRK'
    _cols = 'BEZNR;PGRUPPENCODE;ANZPERSONEN'
    _longformat = True


class Nachfragebeschreibung(VisumTable):
    name = 'Nachfragebeschreibungen'
    code = 'NACHFRAGEBESCHREIBUNG'
    _cols = 'NSEGCODE;NACHFRAGEGLNR;MATRIX'
    _defaults = {'NACHFRAGEGLNR': 1}


class Aktivitaet(VisumTable):
    name = 'Aktivitäten'
    code = 'AKTIVITAET'
    _cols = ('CODE;RANG;NAME;NACHFRAGEMODELLCODE;ISTHEIMATAKTIVITAET;'
             'STRUKTURGROESSENCODES;KOPPLUNGZIEL;RSA;BASE_CODE;'
             'COMPOSITE_ACTIVITIES;AUTOCALIBRATE;CALCDESTMODE;AKTIVITAETSET')

    def create_tables(self,
                      activities: np.recarray,
                      model: str,
                      suffix=''):
        rows = []
        for a in activities:
            row = self.Row(nachfragemodellcode=model)
            row.code = a['code'] + suffix
            row.name = a['name']
            row.strukturgroessencodes = a['potential'] + suffix
            is_home_activity = a['home']
            row.rang = a['rank'] or 1
            row.rsa = a['rsa']
            row.autocalibrate = a['autocalibrate']
            row.istheimataktivitaet = is_home_activity
            row.kopplungziel = is_home_activity
            row.composite_activities = a['composite_activities']
            row.calcdestmode = a['calcdestmode']
            row.base_code = a['base_code']
            rows.append(row)
        self.add_rows(rows)
        self.set_activityset()
        # set the home activity
        self._homeactivity = self.df.loc[self.df.ISTHEIMATAKTIVITAET == 1].index[0]

    @property
    def all_non_composite_activites(self) -> str:
        """returns all the activities that are not composed by others"""
        non_composite = (self.df['ISTHEIMATAKTIVITAET'] | self.df['CALCDESTMODE'])
        codes = self.df.index[non_composite.astype(bool)]
        return ','.join(codes)

    def set_activityset(self):
        """Sets the activityset for the composite activities"""
        activitysets = defaultdict(set)
        for code, act in self.df.iterrows():
            # add the activity itself, if its no composite activity
            if act['CALCDESTMODE'] or act['ISTHEIMATAKTIVITAET']:
                activitysets[code].add(code)
            # if an activity is part of a composite activity
            for comp_act in act['COMPOSITE_ACTIVITIES'].split(','):
                if not comp_act:
                    continue
                # add its code to the activityset of the composite activity
                activitysets[comp_act].add(code)
        for code, activityset in activitysets.items():
            self.df.loc[code, 'AKTIVITAETSET'] = ','.join(activityset)
        # write back the data from the dataframe to the table
        self.update_table_from_df()

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
        ac = ac_code.split('_')
        main_act = ac[np.argmin(np.array([hierarchy[a]
                                          for a in ac]))]
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
            formel='TableLookup(MATRIX Mat: '\
            'Mat[CODE]="VL_Activity_"+[CODE]: Mat[SUMME]) / [TotalTripsRegion]',
        )
        userdefined.add_formel_attribute(
            objid='MODUS',
            name='TripDistance',
            formel='TableLookup(MATRIX Mat: '
            'Mat[CODE]="VL_"+[CODE]: Mat[SUMME]) / [Trips_RegionMitEinpendler]',
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

                matrices.set_category('Activities')
                nr = matrices.add_daten_matrix(
                    code=f'Activity_{t.CODE}',
                    name=f'Gesamtzahl der Wege zu Aktivität {name}',
                    aktivcode=t.CODE,
                    quellaktivitaetset=self.all_non_composite_activites,
                    zielaktivitaetset=t.AKTIVITAETSET,
                )

                matrices.set_category('VL_Activities')
                nr_vl = matrices.add_formel_matrix(
                    code=f'VL_Activity_{t.CODE}',
                    name=f'Fahrleistung Aktivität {name}',
                    formel=f'Matrix([CODE] = "Activity_{t.CODE}") * '
                    'Matrix([CODE] = "KM")',
                    aktivcode=t.CODE,
                    quellaktivitaetset=self.all_non_composite_activites,
                    zielaktivitaetset=t.AKTIVITAETSET,
                )

                if not t.ISTHEIMATAKTIVITAET:
                    matrices.set_category('Activities_Homebased')
                    nr = matrices.add_daten_matrix(
                        code=f'Activity_HomeBased_{t.CODE}',
                        name=f'Gesamtzahl der Wege von der Wohnung zu Aktivität {name}',
                        aktivcode=t.CODE,
                        quellaktivitaetset=self._homeactivity,
                        zielaktivitaetset=t.AKTIVITAETSET,
                    )

                    matrices.set_category('VL_Activities_Homebased')
                    nr_vl = matrices.add_formel_matrix(
                        code=f'VL_Activity_{t.CODE}',
                        name=f'Fahrleistung Wohnnung-Aktivität {name}',
                        formel=f'Matrix([CODE] = "Activity_HomeBased_{t.CODE}") * '
                        'Matrix([CODE] = "KM")',
                        aktivcode=t.CODE,
                        quellaktivitaetset=self._homeactivity,
                        zielaktivitaetset=t.AKTIVITAETSET,
                    )

                # Distanz nach Wohnort
                userdefined.add_formel_attribute(
                    'BEZIRK',
                    name=f'Distance_WohnOrt_{t.CODE}',
                    formel=f'[MATZEILENSUMME({nr_vl:d})] / [MATZEILENSUMME({nr:d})]',
                )
                userdefined.add_formel_attribute(
                    'BEZIRK',
                    name=f'Distance_AktOrt_{t.CODE}',
                    formel=f'[MATSPALTENSUMME({nr_vl:d})] / [MATSPALTENSUMME({nr:d})]',
                )

                #  Wege und Verkehrsleistung nach Oberbezirk
                matrices.set_category('Activities_OBB')
                obb_nr = matrices.add_daten_matrix(
                    code=f'Activity_{t.CODE}_OBB',
                    name=f'Oberbezirks-Matrix Aktivität {name}',
                    aktivcode=t.CODE,
                    bezugstyp='Oberbezirk',
                    quellaktivitaetset=self.all_non_composite_activites,
                    zielaktivitaetset=t.AKTIVITAETSET,
                )
                matrices.set_category('VL_Activities_OBB')
                vl_obb_nr = matrices.add_daten_matrix(
                    code=f'Activity_VL_{t.CODE}_OBB',
                    name=f'Oberbezirks-Matrix VL Aktivität {name}',
                    aktivcode=t.CODE,
                    bezugstyp='Oberbezirk',
                    quellaktivitaetset=self.all_non_composite_activites,
                    zielaktivitaetset=t.AKTIVITAETSET,
                )

                userdefined.add_formel_attribute(
                    'OBERBEZIRK',
                    name=f'Distance_WohnOrt_{t.CODE}',
                    formel=f'[MATZEILENSUMME({vl_obb_nr:d})] / '
                    f'[MATZEILENSUMME({obb_nr:d})]',
                )
                userdefined.add_formel_attribute(
                    'OBERBEZIRK',
                    name=f'Distance_AktOrt_{t.CODE}',
                    formel=f'[MATSPALTENSUMME({vl_obb_nr:d})] / '
                    f'[MATSPALTENSUMME({obb_nr:d})]',
                )
                self.matrixnummern_activity[t.CODE] = nr

                if t.ISTHEIMATAKTIVITAET:
                    self.matrixnummer_activity_w = nr
                    self.matrixnummer_activity_vl_w = nr_vl
                    self.obbmatrixnummer_activity_w = obb_nr
                    self.obbmatrixnummer_activity_vl_w = vl_obb_nr

                if t.RSA:
                    matrices.set_category('Commuters')
                    matrices.add_daten_matrix(
                        code=f'Pendlermatrix_{t.CODE}_OBB',
                        name=f'Oberbezirks-Matrix Pendleraktivität {name}',
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
        matrices.set_category('Activities_Balancing')
        for t in self.table:
            code = t.CODE
            if not code.endswith('_'):
                name = t.NAME

                matrices.set_category('Activities')
                nr = matrices.add_daten_matrix(
                    code=f'AllActivity_{code}',
                    name=f'Gesamtzahl der Gesamtwege zu Aktivität {name}',
                    aktivcode=code,
                    savematrix=savematrix,
                    loadmatrix=loadmatrix,
                )

                if t.RSA:
                    matrices.set_category('Commuters')
                    nr = matrices.add_daten_matrix(
                        code=f'Pendlermatrix_{code}',
                        name=f'Gesamtzahl der PendlerGesamtwege zu Aktivität {name}',
                        aktivcode=code,
                        savematrix=savematrix,
                        loadmatrix=loadmatrix,
                    )
                    # Add KF-Attribute
                    userdefined.add_formel_attribute(
                        objid='BEZIRK',
                        attid=f'ZONE_ACTUAL_TRIPS_{code}',
                        formel=f'[MATSPALTENSUMME({nr:d})]',
                        code=f'Trips_actual_to {code}',
                        name=f'Actual Trips to Zone for Activity {code}',
                    )

                    name = t.NAME
                    userdefined.add_daten_attribute(
                        objid='BEZIRK',
                        name=f'ZP0_{code}',
                        kommentar=f'Basis-Zielpotenzial für Aktivität {code}',
                    )
                    userdefined.add_daten_attribute(
                        objid='BEZIRK',
                        name=f'BF_{code}',
                        kommentar=f'Bilanzfaktor für Aktivität {code}',
                        standardwert=1,
                    )

                    # Ziel-Wege je Bezirk
                    formel = f'[ZP0_{code}] / [NETZ\SUM:BEZIRKE\ZP0_{code}] * '\
                    f'[NETZ\SUM:BEZIRKE\ZONE_ACTUAL_TRIPS_{code}]'
                    userdefined.add_formel_attribute(
                        objid='BEZIRK',
                        attid=f'ZONE_TARGET_TRIPS_{code}',
                        code=f'Target Trips to Zone for {code}',
                        name=f'Target Trips to zone for Activity {code}',
                        formel=formel,
                    )

                    # Korrekturfaktor
                    formel = f'IF([ZONE_ACTUAL_TRIPS_{code}]>0, '\
                        f'[ZONE_TARGET_TRIPS_{code}] / [ZONE_ACTUAL_TRIPS_{code}], 1)'
                    userdefined.add_formel_attribute(
                        objid='BEZIRK',
                        attid=f'ZONE_KF_{code}',
                        code=f'Zonal Korrekturfaktor {code}',
                        name=f'Zonal Korrekturfaktor for Activity {code}',
                        kommentar=f'Bilanzfaktor für Aktivität {code}',
                        formel=formel,
                    )

                    # converged
                    threshold_min = 0.95
                    threshold_max = 1.05
                    formel = f'[MIN:BEZIRKE\ZONE_KF_{code}] < {threshold_min} | '\
                    f'[MAX:BEZIRKE\ZONE_KF_{code}] > {threshold_max}'
                    attid = f'NOT_CONVERGED_{code}'
                    userdefined.add_formel_attribute(
                        objid='NETZ',
                        datentyp='Bool',
                        attid=attid,
                        code=attid,
                        name=f'Randsummenabgleich nicht konvergiert für Aktivität {code}',
                        formel=formel,
                    )
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
        matrices.set_category('OV_Skims_PJT')
        for t in self.table:
            if t.CALCDESTMODE:
                name = t.NAME
                matrices.add_daten_matrix(
                    code=f'PJT_{t.CODE}',
                    name=f'Empfundene Reisezeit für Hauptaktivität {name}',
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
        matrices.set_category('IV_Skims_Parking')
        for t in self.table:
            if t.CALCDESTMODE:
                name = t.NAME
                matrices.add_daten_matrix(
                    code=f'PARKING_{t.CODE}',
                    name=f'Parkwiderstand für Hauptaktivität {name}',
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
            if t.CALCDESTMODE:
                userdefined.add_formel_attribute(
                    'NETZ',
                    name=f'Factor_Ticket_{t.CODE}',
                    formel=formel_ov.format(a=t.CODE)
                )
                userdefined.add_formel_attribute(
                    'NETZ',
                    name=f'Factor_Time_OV_{t.CODE}',
                    formel=formel_time_ov.format(a=t.CODE)
                )
                userdefined.add_formel_attribute(
                    'NETZ',
                    name=f'Factor_Cost_Mitfahrer_{t.CODE}',
                    formel=formel_cost_mitfahrer.format(a=t.CODE)
                )
                userdefined.add_formel_attribute(
                    'NETZ',
                    name=f'Factor_Time_Mitfahrer_{t.CODE}',
                    formel=formel_time_mitfahrer.format(a=t.CODE),
                )

    def add_modal_split(self,
                        userdefined: BenutzerdefiniertesAttribut,
                        matrices: Matrix,
                        params: Params):
        """Add userdefined attributes and Matrices for modal split by activity"""
        formel_trips = 'TableLookup(MATRIX Mat, Mat[CODE]="Activity_{a}_"+[CODE], Mat[SUM])'
        formel_ms = '[TRIPS_ACTIVITY_{a}] / [NETZ\TRIPS_ACTIVITY_{a}]'
        formel_netz_trips = '[SUM:MODI\TRIPS_ACTIVITY_{a}]'

        matrices.set_category('Modes_Demand_Activities')

        for t in self.table:
            if not t.CODE.endswith('_'):
                init_matrix = 0 if t.ISTHEIMATAKTIVITAET else 1
                for mode in params.modes:
                    matrices.set_category('Modes_Demand_Activities')

                    mode_code = mode['code']
                    # add output matrix
                    str_name = f'Wege mit Verkehrsmittel {mode_code} der für Aktivität {t.CODE}'
                    nr = matrices.add_daten_matrix(
                        code=f'Activity_{t.CODE}_{mode_code}',
                        name=str_name,
                        moduscode=mode_code,
                        aktivcode=t.CODE,
                        initmatrix=init_matrix,
                    )
                    ges=self.matrixnummern_activity[t.CODE]
                    userdefined.add_formel_attribute(
                        'BEZIRK',
                        name=f'MS_{mode_code}_Act_{t.CODE}',
                        formel=f'[MATSPALTENSUMME({nr:d})] / '
                        f'[MATSPALTENSUMME({ges:d})]',
                    )

                    if t.ISTHEIMATAKTIVITAET:
                        # add output Oberbezirks-Matrix
                        str_name = f'OBB-Wege mit Verkehrsmittel {mode_code}'
                        f'für Aktivität {t.CODE}'
                        nr_obb = matrices.add_daten_matrix(
                            code=f'OBB_Activity_{t.CODE}_{mode_code}',
                            name=str_name,
                            moduscode=mode_code,
                            aktivcode=t.CODE,
                            bezugstyp='Oberbezirk',
                            initmatrix=0,
                        )

                        ges = self.obbmatrixnummer_activity_w
                        userdefined.add_formel_attribute(
                            'OBERBEZIRK',
                            name=f'MS_Home_Mode_{mode_code}',
                            formel=f'[MATSPALTENSUMME({nr_obb:d})] / '
                            f'[MATSPALTENSUMME({ges:d})]',
                        )

                        ges=self.matrixnummer_activity_w
                        userdefined.add_formel_attribute(
                            'BEZIRK',
                            name=f'MS_Home_Mode_{mode_code}',
                            formel=f'[MATSPALTENSUMME({nr:d})] / '
                            f'[MATSPALTENSUMME({ges:d})]',
                        )

                        # add Verkehrsleistung
                        matrices.set_category('VL_Activities')
                        formel = f'Matrix([CODE]="Activity_{t.CODE}_{mode_code}") '
                        f'* Matrix([CODE] = "KM")'
                        nr_vl = matrices.add_formel_matrix(
                            code=f'VL_Activity_{t.CODE}_{mode_code}',
                            name=f'Verkehrsleistung Aktivität {t.CODE} mit {mode_code}',
                            moduscode=mode_code,
                            aktivcode=t.CODE,
                            formel=formel,
                            bezugstyp='Bezirk',
                            initmatrix=0,
                        )
                        matrices.set_category('VL_Activities_OBB')
                        nr_obb_vl = matrices.add_daten_matrix(
                            code=f'OBB_VL_Activity_{t.CODE}_{mode_code}',
                            name=f'OBB-Verkehrsleistung Aktivität {t.CODE} mit {mode_code}',
                            moduscode=mode_code,
                            aktivcode=t.CODE,
                            bezugstyp='Oberbezirk',
                            initmatrix=0,
                        )
                        userdefined.add_formel_attribute(
                            'OBERBEZIRK',
                            name=f'Distance_Home_{mode_code}',
                            formel=f'[MATZEILENSUMME({nr_obb_vl:d})] / '
                            f'[MATZEILENSUMME({nr_obb:d})]',
                        )
                        userdefined.add_formel_attribute(
                            'BEZIRK',
                            name=f'Distance_Home_{mode_code}',
                            formel=f'[MATZEILENSUMME({nr_vl:d})] / '
                            f'[MATZEILENSUMME({nr:d})]',
                        )

                userdefined.add_daten_attribute(
                    'MODUS',
                    name=f'Target_MS_activity_{t.CODE}',
                )
                userdefined.add_daten_attribute(
                    'MODUS',
                    name=f'const_activity_{t.CODE}',
                    standardwert=0,
                )
                userdefined.add_formel_attribute(
                    'MODUS',
                    name=f'Trips_activity_{t.CODE}',
                    formel=formel_trips.format(a=t.CODE)
                )
                userdefined.add_formel_attribute(
                    'Netz',
                    name=f'TRIPS_ACTIVITY_{t.CODE}',
                    formel=formel_netz_trips.format(a=t.CODE)
                )
                userdefined.add_formel_attribute(
                    'MODUS',
                    name=f'MS_activity_{t.CODE}',
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
                    f'kf_logsum_{t.CODE}',
                    standardwert=1,
                )

                userdefined.add_formel_attribute(
                    'Bezirk',
                    f'kf_logsum_{t.CODE}',
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
                      activitypairs: np.recarray,
                      model: str,
                      suffix=''):
        rows = []
        for a in activitypairs:
            ap_code = a['code']
            origin_code = a['qa'] + suffix
            dest_code = a['za'] + suffix
            ap_new_code = '_'.join([origin_code, dest_code])
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

    def create_tables(self,
                      trip_chain_rates: np.recarray,
                      model: str,
                      suffix=''):
        rows = []
        tcr = pd.DataFrame(trip_chain_rates)
        activity_chains = tcr.groupby('code').first()
        for ac_code, ac in activity_chains.iterrows():
            row = self.Row(code=ac_code,
                           name=ac_code,
                           nachfragemodellcode=model,
                           aktivcodes=ac.Sequence)
            rows.append(row)
        self.add_rows(rows)


class Nachfrageschicht(VisumTable):
    name = 'Nachfrageschichten'
    code = 'NACHFRAGESCHICHT'
    _cols = 'CODE;NAME;NACHFRAGEMODELLCODE;AKTKETTENCODE;PGRUPPENCODES;NSEGSET'

    def create_tables_gg(self,
                         trip_chain_rates: np.recarray,
                         model='VisemGeneration',
                         suffix='_'):
        rows = []
        for tcr in trip_chain_rates:
            row = self.Row(nachfragemodellcode=model)
            pgr_code = tcr['group']
            ac = tcr['code']
            act_seq = tcr['Sequence']
            ac_code = ''.join(act_seq)
            row.name = '_'.join((pgr_code, ac))
            if model == 'VisemT':
                row.code = row.name
            else:
                row.code = '_'.join([pgr_code, ac_code])
            row.aktkettencode = ac_code
            row.pgruppencodes = pgr_code
            rows.append(row)
        self.add_rows(rows)

    def create_tables_gd(self,
                         personengruppe: Personengruppe,
                         nsegset: str = 'A,F,M,P,R',
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
                row.nsegset = nsegset
                rows.append(row)
        self.add_rows(rows)
