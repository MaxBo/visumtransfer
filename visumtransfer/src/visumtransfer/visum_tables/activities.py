# -*- coding: utf-8 -*-

import numpy as np
import pandas as pd
from typing import Dict
from collections import defaultdict
from .base import UserDefinedAttribute, UserDefinedGroup
from .matrices import Matrix
from visumtransfer.visum_table import VisumTable


class Activity(VisumTable):
    name = 'Activities'
    code = 'ACTIVITY'
    _cols = ('CODE;RANK;NAME;DEMANDMODELCODE;ISHOMEACTIVITY;'
             'STRUCTURALPROPCODES;CONSTRAINTDEST;RSA;'
             'COMPOSITE_ACTIVITIES;AUTOCALIBRATE;CALCDESTMODE;ACTIVITYSET;BASE_LS'
             ';ZIELWAHL_FUNKTION;MATRIXCODE_PUT;MATRIXCODE_PARKING')

    def create_tables(self,
                      activities: pd.DataFrame,
                      model: str,
                      suffix=''):
        rows = []
        for idx, a in activities.iterrows():
            row = self.Row(demandmodelcode=model)
            row.code = a['code'] + suffix
            row.name = a['name']
            row.structuralpropcodes = a['potential'] + suffix
            is_home_activity = a['home']
            row.rank = a['rank'] or 1
            row.rsa = a['rsa']
            row.autocalibrate = a['autocalibrate']
            row.ishomeactivity = is_home_activity
            row.constraintdest = is_home_activity
            row.composite_activities = a['composite_activities']
            row.calcdestmode = a['calcdestmode']
            row.zielwahl_funktion = a['ZIELWAHL_FUNKTION']
            row.matrixcode_put = a['MATRIXCODE_PUT']
            row.matrixcode_parking = a['MATRIXCODE_PARKING']
            rows.append(row)
        self.add_rows(rows)
        self.set_activityset()

    @property
    def _homeactivity(self) -> str:
        """get the home activity"""
        return self.df.loc[self.df.ISHOMEACTIVITY == 1].index[0]

    @property
    def all_non_composite_activites(self) -> str:
        """returns all the activities that are not composed by others"""
        non_composite = (self.df['ISHOMEACTIVITY'] | self.df['CALCDESTMODE'])
        codes = self.df.index[non_composite.astype(bool)]
        return ','.join(sorted(codes))

    def set_activityset(self):
        """Sets the activityset for the composite activities"""
        activitysets = defaultdict(set)
        for code, act in self.df.iterrows():
            # add the activity itself, if its no composite activity
            if act['CALCDESTMODE'] or act['ISHOMEACTIVITY']:
                activitysets[code].add(code)
            # if an activity is part of a composite activity
            for comp_act in act['COMPOSITE_ACTIVITIES'].split(','):
                if not comp_act:
                    continue
                # add its code to the activityset of the composite activity
                activitysets[comp_act].add(code)
        for code, activityset in activitysets.items():
            self.df.loc[code, 'ACTIVITYSET'] = ','.join(sorted(activityset))

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
            .sort_values(['ISHOMEACTIVITY', 'RANK', 'CODE'])
        codes = sorted_df[['CODE']].copy()
        codes['idx'] = range(len(codes))
        hierarchy = codes.set_index('CODE').to_dict()['idx']
        return hierarchy

    def add_benutzerdefinierte_attribute(
            self,
            userdef: UserDefinedAttribute):
        """
        Add benutzerdefinierte Attribute for Activities
        """
        userdef.add_formula_attribute(
            objid='ACTIVITY',
            name='TotalTrips',
            formula='TableLookup(MATRIX Mat: '
            'Mat[CODE]="Activity_"+[CODE]: Mat[SUM])',
            comment='Gesamtzahl der Wege'
        )
        userdef.add_formula_attribute(
            objid='ACTIVITY',
            name='TotalTrips_MR',
            formula='TableLookup(MATRIX Mat: '
            'Mat[CODE]="MR_Activity_"+[CODE]: Mat[SUM])',
            comment='Gesamtzahl der Wege von Wohnung aus Modellierungsraum'
        )
        userdef.add_formula_attribute(
            objid='ACTIVITY',
            name='TotalTrips_HB',
            formula='TableLookup(MATRIX Mat: '
            'Mat[CODE]="HB_Activity_"+[CODE]: Mat[SUM])',
            comment='Gesamtzahl der Wege von Wohnung aus im Gesamtraum'
        )
        userdef.add_formula_attribute(
            objid='ACTIVITY',
            name='Pkm_Total',
            formula='TableLookup(MATRIX Mat: '
            'Mat[CODE]="VL_Activity_"+[CODE]: Mat[SUM])',
        )
        userdef.add_formula_attribute(
            objid='ACTIVITY',
            name='Pkm_Modellierungsraum',
            formula='TableLookup(MATRIX Mat: '
            'Mat[CODE]="MR_VL_Activity_"+[CODE]: Mat[SUM])',
        )
        userdef.add_formula_attribute(
            objid='ACTIVITY',
            name='MeanTripDistance',
            comment='Mittlere Wegelänge HomeBased-Wege im Modellierungsraum',
            formula='[Pkm_Modellierungsraum] / [TotalTrips_MR]',
        )
        userdef.add_formula_attribute(
            objid='ACTIVITY',
            name='MeanTripDistance_AllTrips',
            comment='Mittlere Wegelänge Alle Wege',
            formula='[Pkm_Total] / [TotalTrips]',
        )
        userdef.add_data_attribute(
            objid='ACTIVITY',
            name='Target_MeanTripDistance',
        )
        userdef.add_data_attribute(
            objid='ACTIVITY',
            name='WEIGHT_SWT',
            comment='Weight Startwaitingtime for Activity',
            defaultvalue=1,
        )

    def add_output_matrices(self,
                            matrices: Matrix,
                            userdefgroups: UserDefinedGroup,
                            userdef: UserDefinedAttribute, ):
        """
        Add Output Matrices for Activities
        """
        gr_dist_wo = 'Distanz Wohnort'
        gr_dist_act = 'Distanz AktOrt'

        userdefgroups.add(name=gr_dist_wo,
                          description='Mittlere Wegelänge je Aktivität der Wohnbevölkerung')
        userdefgroups.add(name=gr_dist_act,
                          description='Mittlere Wegelänge je Aktivität der Nutzer am Zielort')
        self.matrixnummern_activity = {}
        for code, t in self.df.iterrows():
            name = t.NAME

            matrices.set_category('Activities')
            no = matrices.add_data_matrix(
                code=f'Activity_{code}',
                name=f'Gesamtzahl der Wege zu Aktivität {name}',
                activitycode=code,
                origactivityset=self.all_non_composite_activites,
                destactivityset=t.ACTIVITYSET,
                obb_matrix_ref=f'[CODE]="Activity_OBB_{code}"',
            )

            matrices.set_category('VL_Activities')
            nr_vl = matrices.add_formula_matrix(
                code=f'VL_Activity_{code}',
                name=f'Fahrleistung Aktivität {name}',
                formula=f'Matrix([CODE] = "Activity_{code}") * '
                'Matrix([CODE] = "KM")',
                activitycode=code,
                origactivityset=self.all_non_composite_activites,
                destactivityset=t.ACTIVITYSET,
                obb_matrix_ref=f'[CODE]="Activity_VL_OBB_{code}"',
            )

            if not t.ISHOMEACTIVITY:
                matrices.set_category('Activities_Homebased')
                no = matrices.add_data_matrix(
                    code=f'HB_Activity_{code}',
                    name=f'Gesamtzahl der Wege von der Wohnung zu Aktivität {name}',
                    activitycode=code,
                    origactivityset=self._homeactivity,
                    destactivityset=t.ACTIVITYSET,
                )

                matrices.set_category('VL_Activities_Homebased')
                nr_vl = matrices.add_formula_matrix(
                    code=f'HB_VL_Activity_{code}',
                    name=f'Fahrleistung Wohnung-Aktivität {name}',
                    formula=f'Matrix([CODE] = "HB_Activity_{code}") * '
                    'Matrix([CODE] = "KM")',
                    activitycode=code,
                    origactivityset=self._homeactivity,
                    destactivityset=t.ACTIVITYSET,
                )

                matrices.set_category('Activities_Modellierungsraum')
                no = matrices.add_formula_matrix(
                    code=f'MR_Activity_{code}',
                    name=f'Gesamtzahl der Wege aus dem Modellierungsraum zur Aktivität {name}',
                    formula=f'Matrix([CODE] = "HB_Activity_{code}") * '
                    'FROM[MODELLIERUNGSRAUM]',
                    activitycode=code,
                    origactivityset=self._homeactivity,
                    destactivityset=t.ACTIVITYSET,
                )

                matrices.set_category('VL_Activities_Modellierungsraum')
                nr_vl = matrices.add_formula_matrix(
                    code=f'MR_VL_Activity_{code}',
                    name=f'Fahrleistung Wohnung(im Modellierungsraum)-Aktivität {name}',
                    formula=f'Matrix([CODE] = "HB_VL_Activity_{code}") * '
                    'FROM[MODELLIERUNGSRAUM]',
                    activitycode=code,
                    origactivityset=self._homeactivity,
                    destactivityset=t.ACTIVITYSET,
                )

            # Distanz nach Wohnort
            userdef.add_formula_attribute(
                'ZONE',
                userdefinedgroupname=gr_dist_wo,
                name=f'Distance_WohnOrt_{code}',
                formula=f'[MATROWSUM({nr_vl:d})] / [MATROWSUM({no:d})]',
            )
            userdef.add_formula_attribute(
                'ZONE',
                userdefinedgroupname=gr_dist_act,
                name=f'Distance_AktOrt_{code}',
                formula=f'[MATCOLSUM({nr_vl:d})] / [MATCOLSUM({no:d})]',
            )

            #  Wege und Verkehrsleistung nach Oberbezirk
            matrices.set_category('Activities_OBB')
            obb_nr = matrices.add_data_matrix(
                code=f'Activity_OBB_{code}',
                name=f'Oberbezirks-Matrix Aktivität {name}',
                activitycode=code,
                objecttyperef='Mainzone',
                origactivityset=self.all_non_composite_activites,
                destactivityset=t.ACTIVITYSET,
            )
            matrices.set_category('VL_Activities_OBB')
            vl_obb_nr = matrices.add_data_matrix(
                code=f'Activity_VL_OBB_{code}',
                name=f'Oberbezirks-Matrix VL Aktivität {name}',
                activitycode=code,
                objecttyperef='Mainzone',
                origactivityset=self.all_non_composite_activites,
                destactivityset=t.ACTIVITYSET,
            )

            userdef.add_formula_attribute(
                'MAINZONE',
                userdefinedgroupname=gr_dist_wo,
                name=f'Distance_WohnOrt_{code}',
                formula=f'[MATROWSUM({vl_obb_nr:d})] / '
                f'[MATROWSUM({obb_nr:d})]',
            )
            userdef.add_formula_attribute(
                'MAINZONE',
                userdefinedgroupname=gr_dist_act,
                name=f'Distance_AktOrt_{code}',
                formula=f'[MATCOLSUM({vl_obb_nr:d})] / '
                f'[MATCOLSUM({obb_nr:d})]',
            )
            self.matrixnummern_activity[code] = no

            if t.ISHOMEACTIVITY:
                self.matrixnummer_activity_w = no
                self.matrixnummer_activity_vl_w = nr_vl
                self.obbmatrixnummer_activity_w = obb_nr
                self.obbmatrixnummer_activity_vl_w = vl_obb_nr

    def add_balancing_output_matrices(self,
                                      matrices: Matrix,
                                      userdefgroups: UserDefinedGroup,
                                      userdef: UserDefinedAttribute,
                                      loadmatrix=0,
                                      savematrix=0):
        """
        Add Output Matrices for Activities with Balancing
        """
        gr_rsa = 'Randsummenabgleich'
        userdefgroups.add(name=gr_rsa, description='Attribute für den Randsummenabgleichs')

        converged_attributes = []
        matrices.set_category('Activities_Balancing')
        for code, t in self.df.iterrows():
            name = t.NAME

            if t.RSA:
                matrices.set_category('Commuters')
                no = matrices.add_data_matrix(
                    code=f'Pendlermatrix_{code}',
                    name=f'Gesamtzahl der PendlerGesamtwege zu Aktivität {name}',
                    activitycode=code,
                    savematrix=savematrix,
                    loadmatrix=loadmatrix,
                    obb_matrix_ref=f'[CODE]="Pendlermatrix_OBB_{code}"',
                    matrixfolder='Pendler',
                )
                # Add KF-Attribute
                userdef.add_formula_attribute(
                    objid='ZONE',
                    attid=f'ZONE_ACTUAL_TRIPS_{code}',
                    formula=f'[MATCOLSUM({no:d})]',
                    code=f'Trips_actual_to {code}',
                    name=f'Actual Trips to Zone for Activity {code}',
                    userdefinedgroupname=gr_rsa,
                )

                userdef.add_data_attribute(
                    objid='ZONE',
                    name=f'BF_{code}',
                    comment=f'Bilanzfaktor für Aktivität {code}',
                    defaultvalue=1,
                    userdefinedgroupname=gr_rsa,
                )

                # Ziel-Wege je Bezirk
                formula = fr'[ZP_{code}] / [NETWORK\SUM:ZONES\ZP_{code}] * '\
                    fr'[NETWORK\SUM:ZONES\ZONE_ACTUAL_TRIPS_{code}]'
                userdef.add_formula_attribute(
                    objid='ZONE',
                    attid=f'ZONE_TARGET_TRIPS_{code}',
                    code=f'Target Trips to Zone for {code}',
                    name=f'Target Trips to zone for Activity {code}',
                    formula=formula,
                    userdefinedgroupname=gr_rsa,
                )

                # Korrekturfaktor
                formula = f'IF([ZONE_ACTUAL_TRIPS_{code}]>0, '\
                    f'[ZONE_TARGET_TRIPS_{code}] / [ZONE_ACTUAL_TRIPS_{code}], 1)'
                userdef.add_formula_attribute(
                    objid='ZONE',
                    attid=f'ZONE_KF_{code}',
                    code=f'Zonal Korrekturfaktor {code}',
                    name=f'Zonal Korrekturfaktor for Activity {code}',
                    comment=f'Bilanzfaktor für Aktivität {code}',
                    formula=formula,
                    userdefinedgroupname=gr_rsa,
                )

                # converged
                threshold_min = 0.95
                threshold_max = 1.05
                formula = fr'[MIN:ZONES\ZONE_KF_{code}] < {threshold_min} | '\
                    fr'[MAX:ZONES\ZONE_KF_{code}] > {threshold_max}'
                attid = f'NOT_CONVERGED_{code}'
                userdef.add_formula_attribute(
                    objid='NETWORK',
                    valuetype='Bool',
                    attid=attid,
                    code=attid,
                    name=f'Randsummenabgleich nicht konvergiert für Aktivität {code}',
                    formula=formula,
                    userdefinedgroupname=gr_rsa,
                )
                converged_attributes.append(attid)

                matrices.add_data_matrix(
                    code=f'Pendlermatrix_OBB_{code}',
                    name=f'Oberbezirks-Matrix Pendleraktivität {name}',
                    activitycode=code,
                    objecttyperef='Mainzone',
                    matrixfolder='Pendler',
                )

        formula = ' | '.join((f"[{c}]" for c in converged_attributes))
        attid = 'NOT_CONVERGED_ANY_ACTIVITY'
        userdef.add_formula_attribute(
            objid='NETWORK',
            valuetype='Bool',
            attid=attid,
            code=attid,
            name='Randsummenabgleich nicht konvergiert für mindestens eine Aktivität',
            formula=formula,
            userdefinedgroupname=gr_rsa,
        )

        userdef.add_data_attribute(
            objid='NETWORK',
            name='NOT_CONVERGED_MS_TRIPLENGTH',
            valuetype='Bool',
            defaultvalue=1,
            comment='Modal Split und Wegelängen sind noch nicht konvergiert',
            userdefinedgroupname=gr_rsa,
        )

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
                matrices.add_data_matrix(
                    code=f'PJT_{code}',
                    name=f'Empfundene Reisezeit für Hauptaktivität {name}',
                    matrixtype='Skim',
                    activitycode=code,
                    loadmatrix=0,
                    savematrix=savematrix,
                )

    def add_parkzone_attrs(self,
                           userdefgroups: UserDefinedGroup,
                           userdef: UserDefinedAttribute,
                           n_parkzones: int = 10,
                           ):
        """
        Add Activity-Attributes
        """
        gr_parking = 'Parken'
        userdefgroups.add(name=gr_parking, description='Parkwiderstände')

        for z in range(n_parkzones):
            userdef.add_data_attribute(
                'ACTIVITY',
                name=f'PARKING_ZONE_{z}',
                comment=f'Parkwiderstand für Park-Zone {z}',
                userdefinedgroupname=gr_parking,
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
                matrices.add_data_matrix(
                    code=f'PARKING_{code}',
                    name=f'Parkwiderstand für Hauptaktivität {name}',
                    activitycode=code,
                    matrixtype='Skim',
                    loadmatrix=0,
                    savematrix=savematrix,
                )

    def add_modal_split(self,
                        userdefgroups: UserDefinedGroup,
                        userdef: UserDefinedAttribute,
                        matrices: Matrix,
                        modes: pd.DataFrame):
        """Add userdefined attributes and Matrices for modal split by activity"""

        gr_ms_act = 'Modal Split Aktivität'
        gr_ms = 'Modal Split'
        gr_ms_home = 'Modal Split HomeBased'
        gr_dist = 'Distanz'
        gr_coeff = 'Koeffizienten'
        gr_trips = 'Wege'
        userdefgroups.add(name=gr_ms_act, description='Modal Split nach Aktivität')
        userdefgroups.add(name=gr_ms, description='Modal Split aller Wege')
        userdefgroups.add(name=gr_ms_home, description='Modal Split aller Wege ab Wohnung')
        userdefgroups.add(name=gr_dist, description='Mittlere Länge aller Wege ab Wohnung')
        userdefgroups.add(name=gr_coeff, description='Koeffizienten des Verkehrsmittelwahlmodells')
        userdefgroups.add(name=gr_trips, description='Anzahl der Wege')

        for code, t in self.df.iterrows():
            # not initmatrix at the moment...
            init_matrix = 0
            #init_matrix = 0 if t.ISHOMEACTIVITY else 1
            for _, mode in modes.iterrows():
                matrices.set_category('Modes_Demand_Activities')

                mode_code = mode['code']
                # add output matrix
                str_name = f'Wege mit Verkehrsmittel {mode_code} der für Aktivität {code}'
                obb_matrix_ref = f'[CODE]="OBB_Activity_{code}_{mode_code}"'\
                    if t.ISHOMEACTIVITY else None
                no = matrices.add_data_matrix(
                    code=f'Activity_{code}_{mode_code}',
                    name=str_name,
                    modecode=mode_code,
                    activitycode=code,
                    initmatrix=init_matrix,
                    obb_matrix_ref=obb_matrix_ref,
                )
                ges = self.matrixnummern_activity[code]
                userdef.add_formula_attribute(
                    'ZONE',
                    userdefinedgroupname=gr_ms_act,
                    name=f'MS_{mode_code}_Act_{code}',
                    formula=f'[MATCOLSUM({no:d})] / '
                    f'[MATCOLSUM({ges:d})]',
                )

                if t.ISHOMEACTIVITY:
                    # add output Oberbezirks-Matrix
                    str_name = f'OBB-Wege mit Verkehrsmittel {mode_code}'
                    f'für Aktivität {code}'
                    nr_obb = matrices.add_data_matrix(
                        code=f'OBB_Activity_{code}_{mode_code}',
                        name=str_name,
                        modecode=mode_code,
                        activitycode=code,
                        objecttyperef='Mainzone',
                        initmatrix=0,
                    )

                    ges = self.obbmatrixnummer_activity_w
                    userdef.add_formula_attribute(
                        'MAINZONE',
                        userdefinedgroupname=gr_ms_home,
                        name=f'MS_Home_Mode_{mode_code}',
                        formula=f'[MATCOLSUM({nr_obb:d})] / '
                        f'[MATCOLSUM({ges:d})]',
                    )

                    ges = self.matrixnummer_activity_w
                    userdef.add_formula_attribute(
                        'ZONE',
                        userdefinedgroupname=gr_ms_home,
                        name=f'MS_Home_Mode_{mode_code}',
                        formula=f'[MATCOLSUM({no:d})] / '
                        f'[MATCOLSUM({ges:d})]',
                    )

                    # add Verkehrsleistung
                    matrices.set_category('VL_Activities')
                    formula = f'Matrix([CODE]="Activity_{code}_{mode_code}") '\
                        f'* Matrix([CODE] = "KM")'
                    nr_vl = matrices.add_formula_matrix(
                        code=f'VL_Activity_{code}_{mode_code}',
                        name=f'Verkehrsleistung Aktivität {code} mit {mode_code}',
                        modecode=mode_code,
                        activitycode=code,
                        formula=formula,
                        objecttyperef='Zone',
                        initmatrix=0,
                    )
                    matrices.set_category('VL_Activities_OBB')
                    nr_obb_vl = matrices.add_data_matrix(
                        code=f'OBB_VL_Activity_{code}_{mode_code}',
                        name=f'OBB-Verkehrsleistung Aktivität {code} mit {mode_code}',
                        modecode=mode_code,
                        activitycode=code,
                        objecttyperef='Mainzone',
                        initmatrix=0,
                    )
                    userdef.add_formula_attribute(
                        'MAINZONE',
                        userdefinedgroupname=gr_dist,
                        name=f'Distance_Home_{mode_code}',
                        formula=f'[MATROWSUM({nr_obb_vl:d})] / '
                        f'[MATROWSUM({nr_obb:d})]',
                    )
                    userdef.add_formula_attribute(
                        'ZONE',
                        userdefinedgroupname=gr_dist,
                        name=f'Distance_Home_{mode_code}',
                        formula=f'[MATROWSUM({nr_vl:d})] / '
                        f'[MATROWSUM({no:d})]',
                    )

        # Add User Defined Attributes for the trips
        formel_trips_mode = 'TableLookup(MATRIX Mat, Mat[CODE]="Activity_"+[CODE]+"_{m}", Mat[SUM])'
        formel_trips = 'TableLookup(MATRIX Mat, Mat[CODE]="Activity_"+[CODE], Mat[SUM])'
        formel_ms = '[TRIPS_{m}] / [TotalTrips_HB]'

        userdef.add_formula_attribute(
            'ACTIVITY',
            userdefinedgroupname=gr_trips,
            name='Trips',
            formula=formel_trips.format(m=mode.code)
        )
        for _, mode in modes.iterrows():
            userdef.add_data_attribute(
                'ACTIVITY',
                userdefinedgroupname=gr_ms,
                name=f'Target_MS_{mode.code}',
                comment=f'Modal Split (Zielwert) {mode.bezeichnung}',
            )
            userdef.add_data_attribute(
                'ACTIVITY',
                userdefinedgroupname=gr_coeff,
                name=f'baseconst_{mode.code}',
                comment=f'Verkehrsmittelspezifische Basis-Konstante {mode.bezeichnung}',
                defaultvalue=0,
            )
            userdef.add_data_attribute(
                'ACTIVITY',
                userdefinedgroupname=gr_coeff,
                name=f'KF_CONST_{mode.code}',
                comment=f'Korrekturfaktor für Kalibrierung MS {mode.bezeichnung}',
                defaultvalue=0,
            )
            userdef.add_formula_attribute(
                'ACTIVITY',
                userdefinedgroupname=gr_trips,
                name=f'Trips_{mode.code}',
                comment=f'Wege {mode.bezeichnung}',
                formula=formel_trips_mode.format(m=mode.code)
            )
            userdef.add_formula_attribute(
                'ACTIVITY',
                userdefinedgroupname=gr_ms,
                name=f'MS_{mode.code}',
                comment=f'Modal Split modelliert {mode.bezeichnung}',
                formula=formel_ms.format(m=mode.code)
            )
            userdef.add_data_attribute(
                'ACTIVITY',
                userdefinedgroupname=gr_coeff,
                name=f'FACTOR_TIME_{mode.code}',
                comment=f'Faktor Reisezeitkoeffizient {mode.bezeichnung}',
                defaultvalue=1,
            )
            userdef.add_data_attribute(
                'ACTIVITY',
                userdefinedgroupname=gr_coeff,
                name=f'FACTOR_COST_{mode.code}',
                comment=f'Faktor Kostenkoeffizient {mode.bezeichnung}',
                defaultvalue=1,
            )

    def add_kf_logsum(self,
                      userdefgroups: UserDefinedGroup,
                      userdef: UserDefinedAttribute,
                      ):
        """
        add Korrekturfaktoren für Widerstandsempfindlichkeit auf Bezirksebene je Aktivität
        Zielwahlmodell zur Korrektur der Wegelängen verwendet
        """
        gr_kf_ls = 'Zielwahl-Parameter'
        userdefgroups.add(name=gr_kf_ls, description='Parameter des Zielwahl-Modells')

        for code, t in self.df.iterrows():
            if t.CALCDESTMODE:
                userdef.add_data_attribute(
                    'ZONE',
                    f'impedance_sensitivity_{code}',
                    defaultvalue=1,
                    userdefinedgroupname=gr_kf_ls,
                )


class Activitypair(VisumTable):
    name = 'Activitypairs'
    code = 'ACTPAIR'
    _cols = 'CODE;NAME;DEMANDMODELCODE;ORIGACTIVITYCODE;DESTACTIVITYCODE;ORIGDESTTYPE'
    _pkey = 'CODE'
    _defaults = {'ORIGDESTTYPE': 3,
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
                           demandmodelcode=model,
                           origactivitycode=origin_code,
                           destactivitycode=dest_code)
            rows.append(row)
        self.add_rows(rows)


class Activitychain(VisumTable):
    name = 'Activitychains'
    code = 'ACTCHAIN'
    _cols = 'CODE;NAME;DEMANDMODELCODE;ACTIVITYCODES'
    _pkey = 'CODE'

    def create_tables(self,
                      trip_chain_rates: pd.DataFrame,
                      model: str):
        rows = []
        activity_chains = trip_chain_rates.groupby('code_tc').first()
        for ac_code, ac in activity_chains.iterrows():
            row = self.Row(code=ac_code,
                           name=ac_code,
                           demandmodelcode=model,
                           activitycodes=ac.Sequence)
            rows.append(row)
        self.add_rows(rows)
