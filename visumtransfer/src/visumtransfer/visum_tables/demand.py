# -*- coding: utf-8 -*-

import numpy as np
import pandas as pd
import json
from typing import Dict
from collections import defaultdict
from .matrizen import Matrix
from .basis import BenutzerdefiniertesAttribut
from visumtransfer.visum_table import (VisumTable)
from visumtransfer.params import Params



class Nachfragemodell(VisumTable):
    name = 'Nachfragemodelle'
    code = 'NACHFRAGEMODELL'
    _cols = 'CODE;NAME;TYP;MODUSSET'


class Personengruppe(VisumTable):
    name = 'Personengruppen'
    code = 'PERSONENGRUPPE'
    _cols = 'CODE;NAME;NACHFRAGEMODELLCODE'

    def __init__(self, mode='+'):
        super(Personengruppe, self).__init__(mode=mode)
        self.groups = []
        self.gd_codes = defaultdict(list)

    def add_group(self, code: str, model_code: str, **kwargs):
        row = self.Row(code=code,
                       nachfragemodellcode=model_code,
                       **kwargs)
        self.groups.append(row)

    def create_groups_destmode(self,
                               groups_generation: pd.DataFrame,
                               trip_chain_rates: pd.DataFrame,
                               activities: 'Aktivitaet',
                               model_code: str,
                               category: str,
                               ):
        """"""

        assert isinstance(activities, Aktivitaet)
        act_hierarchy = activities.get_hierarchy()

        # merge persongroups to tripchainrates
        gds = trip_chain_rates.groupby(['group_generation', 'code'])\
            .first()\
            .reset_index()\
            .set_index('group_generation')
        gds = gds.merge(groups_generation, left_index=True, right_on='code',
                        suffixes=['_tc', '_person'])

        # loop over all tripchains in the groups
        for _, tc in gds.iterrows():
            gg_code = tc['code']
            gd_code = tc['group']
            act_code = tc['code_tc']
            act_sequence = tc['Sequence']
            tc_name = tc['name']
            main_act = activities.get_main_activity(act_hierarchy, act_sequence)
            code = '_'.join((gd_code, main_act))
            # if the the group occurs the first time ...
            if code not in self.gd_codes:
                #  create it and add it to self.gd_codes
                self.gd_codes[code] = [act_code]
                name = f'{tc_name} mit Hauptaktivität {main_act}'

                self.add_group(
                    category=category,
                    model_code=model_code,
                    code=code,
                    name=name,
                    groups_constants=tc['groups_constants'],
                    groups_output=tc['groups_output'],
                    group_generation=gg_code,
                    main_act=main_act)
            else:
                # otherwise just append the activity chain
                # to the chains the persons makes
                self.gd_codes[code].append(act_code)

    def create_df_from_group_list(self):
        df = self.df_from_array(self.groups)
        self.add_df(df)

    def add_calibration_matrices_and_attributes(
            self,
            modes: pd.DataFrame,
            matrices: Matrix):
        """
        Add Output Matrices for PersonGroups
        """
        matrices.set_category('Demand_Pgr')
        df_groups_output = self.df['GROUPS_OUTPUT'].str.split(',', expand=True)
        df_groups_output.columns = [f'group{i}'
                                    for i in df_groups_output.columns]
        df_out_long = pd.wide_to_long(df_groups_output.reset_index(),
                                      'group',
                                      'CODE',
                                      'gr_id')
        df_out_long = df_out_long.loc[~df_out_long['group'].isnull()]
        df_out_long.set_index(df_out_long.index.droplevel(level=1), inplace=True)
        prefix = 'Pgr_'

        for group_output, detailed_groups in df_out_long.groupby(by='group'):
            gr = self.df.loc[group_output]
            str_name = f'Wege der {gr.CATEGORY}-Gruppe {gr.NAME}'
            code = f'{prefix}{gr.name}'
            pgrset = ','.join(detailed_groups.index)
            matrices.add_daten_matrix(
                code=code,
                name=str_name,
                modusset=','.join(modes['code']),
                personengruppenset=pgrset,
                pgruppencode=group_output,
            )
            vl_code = f'VL_{code}'
            formel_vl = f'Matrix([CODE]="{code}") * Matrix([CODE]="KM")'
            vl_name = f'Verkehrsleistung der {gr.CATEGORY}-Gruppe {gr.NAME}'

            matrices.add_formel_matrix(
                code=vl_code,
                formel=formel_vl,
                name=vl_name,
                modusset=','.join(modes['code']),
                personengruppenset=pgrset,
                pgruppencode=group_output,
            )

            for _, mode in modes.iterrows():
                mode_name = mode['name']
                # add output matrix
                str_name = f'Wege mit Verkehrsmittel {mode_name} der {gr.CATEGORY}-Gruppe {gr.NAME}'
                code = f'{prefix}{gr.name}_{mode.code}'
                pgrset = ','.join(detailed_groups.index)
                matrices.add_daten_matrix(
                    code=code,
                    name=str_name,
                    moduscode=mode.code,
                    modusset=mode.code,
                    personengruppenset=pgrset,
                    pgruppencode=group_output,
                )
                vl_code = f'VL_{code}'
                formel_vl = f'Matrix([CODE]="{code}") * Matrix([CODE]="KM")'
                vl_name = f'Verkehrsleistung mit Verkehrsmittel {mode_name} der {gr.CATEGORY}-Gruppe {gr.NAME}'
                matrices.add_formel_matrix(
                    code=vl_code,
                    formel=formel_vl,
                    name=vl_name,
                    modusset=','.join(modes['code']),
                    personengruppenset=pgrset,
                    pgruppencode=group_output,
                )

class Strukturgr(VisumTable):
    name = 'Strukturgrößen'
    code = 'STRUKTURGROESSE'
    _cols = 'CODE;NAME;NACHFRAGEMODELLCODE'

    def create_tables(self,
                      activities: pd.DataFrame,
                      model: str,
                      suffix=''):
        rows = []
        for idx, a in activities.iterrows():
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
             'STRUKTURGROESSENCODES;KOPPLUNGZIEL;RSA;'
             'COMPOSITE_ACTIVITIES;AUTOCALIBRATE;CALCDESTMODE;AKTIVITAETSET;BASE_LS')

    def create_tables(self,
                      activities: pd.DataFrame,
                      model: str,
                      suffix=''):
        rows = []
        for idx, a in activities.iterrows():
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
            rows.append(row)
        self.add_rows(rows)
        self.set_activityset()

    @property
    def _homeactivity(self) -> str:
        """get the home activity"""
        return self.df.loc[self.df.ISTHEIMATAKTIVITAET == 1].index[0]

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

    def get_main_activity(self, hierarchy: Dict[str, int], ac_sequence: str) -> str:
        """get the code of the main activity from ac_code

        Parameters
        ----------
        hierarchy : dict
            the hierarchy-dict produced by self.get_hierarchy()
        ac_sequence : str
            the Activity-Chain-Sequence like W,A,E,W

        Returns
        -------
        main_activity : str
        """
        ac = ac_sequence.split(',')
        main_act = ac[np.argmin(np.array([hierarchy[a]
                                          for a in ac]))]
        return main_act

    def get_hierarchy(self) -> Dict[str, int]:
        """
        Return a dict with the hierarchy of activities

        Returns
        -------
        hierarchy : dict
        """
        sorted_df = self.df.reset_index()\
            .sort_values(['ISTHEIMATAKTIVITAET', 'RANG', 'CODE'])
        codes = sorted_df[['CODE']].copy()
        codes['idx'] = range(len(codes))
        hierarchy = codes.set_index('CODE').to_dict()['idx']
        return hierarchy

    def add_benutzerdefinierte_attribute(
            self,
            userdef: BenutzerdefiniertesAttribut):
        """
        Add benutzerdefinierte Attribute for Activities
        """
        userdef.add_formel_attribute(
            objid='AKTIVITAET',
            name='TotalTrips',
            formel='TableLookup(MATRIX Mat: '
            'Mat[CODE]="Activity_"+[CODE]: Mat[SUMME])',
            kommentar='Gesamtzahl der Wege'
        )
        userdef.add_formel_attribute(
            objid='AKTIVITAET',
            name='MeanTripDistance',
            formel='TableLookup(MATRIX Mat: '
            'Mat[CODE]="VL_Activity_"+[CODE]: Mat[SUMME]) / [TotalTrips]',
        )
        userdef.add_daten_attribute(
            objid='AKTIVITAET',
            name='Target_MeanTripDistance',
        )
        userdef.add_daten_attribute(
            objid='AKTIVITAET',
            name='TTFACTOR_O',
            kommentar='Anpassung Reisezeitkoeffizient ÖV für Aktivität',
            standardwert=1,
        )
        userdef.add_daten_attribute(
            objid='AKTIVITAET',
            name='TTFACTOR_M',
            kommentar='Anpassung Reisezeitkoeffizient Mitfahrer für Aktivität',
            standardwert=1,
        )

    def add_output_matrices(self,
                            matrices: Matrix,
                            userdef: BenutzerdefiniertesAttribut, ):
        """
        Add Output Matrices for Activities
        """
        self.matrixnummern_activity = {}
        for code, t in self.df.iterrows():
            name = t.NAME

            matrices.set_category('Activities')
            nr = matrices.add_daten_matrix(
                code=f'Activity_{code}',
                name=f'Gesamtzahl der Wege zu Aktivität {name}',
                aktivcode=code,
                quellaktivitaetset=self.all_non_composite_activites,
                zielaktivitaetset=t.AKTIVITAETSET,
            )

            matrices.set_category('VL_Activities')
            nr_vl = matrices.add_formel_matrix(
                code=f'VL_Activity_{code}',
                name=f'Fahrleistung Aktivität {name}',
                formel=f'Matrix([CODE] = "Activity_{code}") * '
                'Matrix([CODE] = "KM")',
                aktivcode=code,
                quellaktivitaetset=self.all_non_composite_activites,
                zielaktivitaetset=t.AKTIVITAETSET,
            )

            if not t.ISTHEIMATAKTIVITAET:
                matrices.set_category('Activities_Homebased')
                nr = matrices.add_daten_matrix(
                    code=f'Activity_HomeBased_{code}',
                    name=f'Gesamtzahl der Wege von der Wohnung zu Aktivität {name}',
                    aktivcode=code,
                    quellaktivitaetset=self._homeactivity,
                    zielaktivitaetset=t.AKTIVITAETSET,
                )

                matrices.set_category('VL_Activities_Homebased')
                nr_vl = matrices.add_formel_matrix(
                    code=f'VL_Activity_{code}',
                    name=f'Fahrleistung Wohnnung-Aktivität {name}',
                    formel=f'Matrix([CODE] = "Activity_HomeBased_{code}") * '
                    'Matrix([CODE] = "KM")',
                    aktivcode=code,
                    quellaktivitaetset=self._homeactivity,
                    zielaktivitaetset=t.AKTIVITAETSET,
                )

            # Distanz nach Wohnort
            userdef.add_formel_attribute(
                'BEZIRK',
                name=f'Distance_WohnOrt_{code}',
                formel=f'[MATZEILENSUMME({nr_vl:d})] / [MATZEILENSUMME({nr:d})]',
            )
            userdef.add_formel_attribute(
                'BEZIRK',
                name=f'Distance_AktOrt_{code}',
                formel=f'[MATSPALTENSUMME({nr_vl:d})] / [MATSPALTENSUMME({nr:d})]',
            )

            #  Wege und Verkehrsleistung nach Oberbezirk
            matrices.set_category('Activities_OBB')
            obb_nr = matrices.add_daten_matrix(
                code=f'Activity_OBB_{code}',
                name=f'Oberbezirks-Matrix Aktivität {name}',
                aktivcode=code,
                bezugstyp='Oberbezirk',
                quellaktivitaetset=self.all_non_composite_activites,
                zielaktivitaetset=t.AKTIVITAETSET,
            )
            matrices.set_category('VL_Activities_OBB')
            vl_obb_nr = matrices.add_daten_matrix(
                code=f'Activity_VL_OBB_{code}',
                name=f'Oberbezirks-Matrix VL Aktivität {name}',
                aktivcode=code,
                bezugstyp='Oberbezirk',
                quellaktivitaetset=self.all_non_composite_activites,
                zielaktivitaetset=t.AKTIVITAETSET,
            )

            userdef.add_formel_attribute(
                'OBERBEZIRK',
                name=f'Distance_WohnOrt_{code}',
                formel=f'[MATZEILENSUMME({vl_obb_nr:d})] / '
                f'[MATZEILENSUMME({obb_nr:d})]',
            )
            userdef.add_formel_attribute(
                'OBERBEZIRK',
                name=f'Distance_AktOrt_{code}',
                formel=f'[MATSPALTENSUMME({vl_obb_nr:d})] / '
                f'[MATSPALTENSUMME({obb_nr:d})]',
            )
            self.matrixnummern_activity[code] = nr

            if t.ISTHEIMATAKTIVITAET:
                self.matrixnummer_activity_w = nr
                self.matrixnummer_activity_vl_w = nr_vl
                self.obbmatrixnummer_activity_w = obb_nr
                self.obbmatrixnummer_activity_vl_w = vl_obb_nr


    def add_balancing_output_matrices(self,
                                      matrices: Matrix,
                                      userdef: BenutzerdefiniertesAttribut,
                                      loadmatrix=0,
                                      savematrix=1):
        """
        Add Output Matrices for Activities with Balancing
        """
        converged_attributes = []
        matrices.set_category('Activities_Balancing')
        for code, t in self.df.iterrows():
            name = t.NAME

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
                userdef.add_formel_attribute(
                    objid='BEZIRK',
                    attid=f'ZONE_ACTUAL_TRIPS_{code}',
                    formel=f'[MATSPALTENSUMME({nr:d})]',
                    code=f'Trips_actual_to {code}',
                    name=f'Actual Trips to Zone for Activity {code}',
                )

                name = t.NAME
                userdef.add_daten_attribute(
                    objid='BEZIRK',
                    name=f'ZP0_{code}',
                    kommentar=f'Basis-Zielpotenzial für Aktivität {code}',
                )
                userdef.add_daten_attribute(
                    objid='BEZIRK',
                    name=f'BF_{code}',
                    kommentar=f'Bilanzfaktor für Aktivität {code}',
                    standardwert=1,
                )

                # Ziel-Wege je Bezirk
                formel = f'[ZP0_{code}] / [NETZ\SUM:BEZIRKE\ZP0_{code}] * '\
                f'[NETZ\SUM:BEZIRKE\ZONE_ACTUAL_TRIPS_{code}]'
                userdef.add_formel_attribute(
                    objid='BEZIRK',
                    attid=f'ZONE_TARGET_TRIPS_{code}',
                    code=f'Target Trips to Zone for {code}',
                    name=f'Target Trips to zone for Activity {code}',
                    formel=formel,
                )

                # Korrekturfaktor
                formel = f'IF([ZONE_ACTUAL_TRIPS_{code}]>0, '\
                    f'[ZONE_TARGET_TRIPS_{code}] / [ZONE_ACTUAL_TRIPS_{code}], 1)'
                userdef.add_formel_attribute(
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
                userdef.add_formel_attribute(
                    objid='NETZ',
                    datentyp='Bool',
                    attid=attid,
                    code=attid,
                    name=f'Randsummenabgleich nicht konvergiert für Aktivität {code}',
                    formel=formel,
                )
                converged_attributes.append(attid)

                matrices.add_daten_matrix(
                    code=f'Pendlermatrix_{code}_OBB',
                    name=f'Oberbezirks-Matrix Pendleraktivität {name}',
                    aktivcode=code,
                    bezugstyp='Oberbezirk',
                )

        formel = ' | '.join((f"[{c}]" for c in converged_attributes))
        attid = 'NOT_CONVERGED_ANY_ACTIVITY'
        userdef.add_formel_attribute(
            objid='NETZ',
            datentyp='Bool',
            attid=attid,
            code=attid,
            name='Randsummenabgleich nicht konvergiert für mindestens eine Aktivität',
            formel=formel)

        userdef.add_daten_attribute(
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
        for code, t in self.df.iterrows():
            if t.CALCDESTMODE:
                name = t.NAME
                matrices.add_daten_matrix(
                    code=f'PJT_{code}',
                    name=f'Empfundene Reisezeit für Hauptaktivität {name}',
                    matrixtyp='Kenngröße',
                    aktivcode=code,
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
        for code, t in self.df.iterrows():
            if t.CALCDESTMODE:
                name = t.NAME
                matrices.add_daten_matrix(
                    code=f'PARKING_{code}',
                    name=f'Parkwiderstand für Hauptaktivität {name}',
                    aktivcode=code,
                    matrixtyp='Kenngröße',
                    loadmatrix=1,
                    savematrix=savematrix,
                )

    def add_net_activity_ticket_attributes(self,
                                           userdef: BenutzerdefiniertesAttribut):
        """Add userdefined attributes for ticket costs"""
        formel_ov = 'TableLookup(ACTIVITY Act: Act[CODE]="{a}": Act[HRF_EINZEL2ZEITKARTE])'
        formel_time_ov = 'TableLookup(ACTIVITY Act: Act[CODE]="{a}": Act[TTFACTOR_O])'
        formel_cost_mitfahrer = 'TableLookup(ACTIVITY Act: Act[CODE]="{a}": Act[HRF_COST_MITFAHRER])'
        formel_time_mitfahrer = 'TableLookup(ACTIVITY Act: Act[CODE]="{a}": Act[TTFACTOR_M])'

        for code, t in self.df.iterrows():
            if t.CALCDESTMODE:
                userdef.add_formel_attribute(
                    'NETZ',
                    name=f'Factor_Ticket_{code}',
                    formel=formel_ov.format(a=code)
                )
                userdef.add_formel_attribute(
                    'NETZ',
                    name=f'Factor_Time_OV_{code}',
                    formel=formel_time_ov.format(a=code)
                )
                userdef.add_formel_attribute(
                    'NETZ',
                    name=f'Factor_Cost_Mitfahrer_{code}',
                    formel=formel_cost_mitfahrer.format(a=code)
                )
                userdef.add_formel_attribute(
                    'NETZ',
                    name=f'Factor_Time_Mitfahrer_{code}',
                    formel=formel_time_mitfahrer.format(a=code),
                )

    def add_modal_split(self,
                        userdef: BenutzerdefiniertesAttribut,
                        matrices: Matrix,
                        modes: pd.DataFrame):
        """Add userdefined attributes and Matrices for modal split by activity"""

        for code, t in self.df.iterrows():
            init_matrix = 0 if t.ISTHEIMATAKTIVITAET else 1
            for _, mode in modes.iterrows():
                matrices.set_category('Modes_Demand_Activities')

                mode_code = mode['code']
                # add output matrix
                str_name = f'Wege mit Verkehrsmittel {mode_code} der für Aktivität {code}'
                nr = matrices.add_daten_matrix(
                    code=f'Activity_{code}_{mode_code}',
                    name=str_name,
                    moduscode=mode_code,
                    aktivcode=code,
                    initmatrix=init_matrix,
                )
                ges=self.matrixnummern_activity[code]
                userdef.add_formel_attribute(
                    'BEZIRK',
                    name=f'MS_{mode_code}_Act_{code}',
                    formel=f'[MATSPALTENSUMME({nr:d})] / '
                    f'[MATSPALTENSUMME({ges:d})]',
                )

                if t.ISTHEIMATAKTIVITAET:
                    # add output Oberbezirks-Matrix
                    str_name = f'OBB-Wege mit Verkehrsmittel {mode_code}'
                    f'für Aktivität {code}'
                    nr_obb = matrices.add_daten_matrix(
                        code=f'OBB_Activity_{code}_{mode_code}',
                        name=str_name,
                        moduscode=mode_code,
                        aktivcode=code,
                        bezugstyp='Oberbezirk',
                        initmatrix=0,
                    )

                    ges = self.obbmatrixnummer_activity_w
                    userdef.add_formel_attribute(
                        'OBERBEZIRK',
                        name=f'MS_Home_Mode_{mode_code}',
                        formel=f'[MATSPALTENSUMME({nr_obb:d})] / '
                        f'[MATSPALTENSUMME({ges:d})]',
                    )

                    ges=self.matrixnummer_activity_w
                    userdef.add_formel_attribute(
                        'BEZIRK',
                        name=f'MS_Home_Mode_{mode_code}',
                        formel=f'[MATSPALTENSUMME({nr:d})] / '
                        f'[MATSPALTENSUMME({ges:d})]',
                    )

                    # add Verkehrsleistung
                    matrices.set_category('VL_Activities')
                    formel = f'Matrix([CODE]="Activity_{code}_{mode_code}") '
                    f'* Matrix([CODE] = "KM")'
                    nr_vl = matrices.add_formel_matrix(
                        code=f'VL_Activity_{code}_{mode_code}',
                        name=f'Verkehrsleistung Aktivität {code} mit {mode_code}',
                        moduscode=mode_code,
                        aktivcode=code,
                        formel=formel,
                        bezugstyp='Bezirk',
                        initmatrix=0,
                    )
                    matrices.set_category('VL_Activities_OBB')
                    nr_obb_vl = matrices.add_daten_matrix(
                        code=f'OBB_VL_Activity_{code}_{mode_code}',
                        name=f'OBB-Verkehrsleistung Aktivität {code} mit {mode_code}',
                        moduscode=mode_code,
                        aktivcode=code,
                        bezugstyp='Oberbezirk',
                        initmatrix=0,
                    )
                    userdef.add_formel_attribute(
                        'OBERBEZIRK',
                        name=f'Distance_Home_{mode_code}',
                        formel=f'[MATZEILENSUMME({nr_obb_vl:d})] / '
                        f'[MATZEILENSUMME({nr_obb:d})]',
                    )
                    userdef.add_formel_attribute(
                        'BEZIRK',
                        name=f'Distance_Home_{mode_code}',
                        formel=f'[MATZEILENSUMME({nr_vl:d})] / '
                        f'[MATZEILENSUMME({nr:d})]',
                    )

        # Add User Defined Attributes for the trips
        formel_trips_mode = 'TableLookup(MATRIX Mat, Mat[CODE]="Activity_"+[CODE]+"_{m}", Mat[SUM])'
        formel_trips = 'TableLookup(MATRIX Mat, Mat[CODE]="Activity_"+[CODE], Mat[SUM])'
        formel_ms = '[TRIPS_{m}] / [TRIPS]'

        userdef.add_formel_attribute(
            'AKTIVITAET',
            name='Trips',
            formel=formel_trips.format(m=mode.code)
        )
        for _, mode in modes.iterrows():
            userdef.add_daten_attribute(
                'AKTIVITAET',
                name=f'Target_MS_{mode.code}',
            )
            userdef.add_daten_attribute(
                'AKTIVITAET',
                name=f'const_{mode.code}',
                standardwert=0,
            )
            userdef.add_daten_attribute(
                'AKTIVITAET',
                name=f'baseconst_{mode.code}',
                standardwert=0,
            )
            userdef.add_formel_attribute(
                'AKTIVITAET',
                name=f'Trips_{mode.code}',
                formel=formel_trips_mode.format(m=mode.code)
            )
            userdef.add_formel_attribute(
                'AKTIVITAET',
                name=f'MS_{mode.code}',
                formel=formel_ms.format(m=mode.code)
            )

    def add_kf_logsum(self,
                      userdef: BenutzerdefiniertesAttribut,
                      ):
        """
        add Korrekturfaktoren für Logsum-Formeln auf Oberbezirksebene
        Dieser werden dann auf Bezirksebene übertragen und im
        Zielwahlmodell zur Korrektur der Wegelängen verwendet
        """
        reference_column = 'OBERBEZIRK_SRV'
        formel = 'TableLookup(MAINZONE OBB, OBB[NO]=[{col}], OBB[KF_LOGSUM_{a}])'
        for code, t in self.df.iterrows():
            if not t.ISTHEIMATAKTIVITAET:
                userdef.add_daten_attribute(
                    'Oberbezirk',
                    f'kf_logsum_{code}',
                    standardwert=1,
                )

                userdef.add_formel_attribute(
                    'Bezirk',
                    f'kf_logsum_{code}',
                    formel=formel.format(col=reference_column,
                                         a=code),
                )


class Aktivitaetenpaar(VisumTable):
    name = 'Aktivitätenpaare'
    code = 'AKTIVITAETENPAAR'
    _cols = 'CODE;NAME;NACHFRAGEMODELLCODE;QUELLAKTIVITAETCODE;ZIELAKTIVITAETCODE;QUELLEZIELTYP'
    _pkey = 'CODE'
    _defaults = {'QUELLZIELTYP': 3,
                 }

    def create_tables(self,
                      activitypairs: pd.DataFrame,
                      model: str):
        rows = []
        for idx, a in activitypairs.iterrows():
            ap_code = a['code']
            origin_code = a['qa']
            dest_code = a['za']
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
                      trip_chain_rates: pd.DataFrame,
                      model: str):
        rows = []
        activity_chains = trip_chain_rates.groupby('code').first()
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

    def create_tables_gd(self,
                         personengruppe: Personengruppe,
                         nsegset: str = 'A,F,M,P,R',
                         model: str = 'VisemGGR',
                         category: str = 'ZielVMWahl'):
        rows = []
        pgroups = personengruppe.df
        pg_gd = pgroups.loc[pgroups['CATEGORY'] == category]
        for pgr_code, gd in pg_gd.iterrows():
            for ac_code in personengruppe.gd_codes[pgr_code]:
                dstratcode = ':'.join((pgr_code, ac_code))
                row = self.Row(code=dstratcode,
                               name=dstratcode,
                               nachfragemodellcode=model,
                               pgruppencodes=pgr_code,
                               aktkettencode=ac_code,
                               nsegset=nsegset,
                               )
                rows.append(row)
        self.add_rows(rows)
