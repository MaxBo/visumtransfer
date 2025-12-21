# -*- coding: utf-8 -*-


import os
import pandas as pd
from argparse import ArgumentParser
from typing import List

from visumtransfer.visum_table import (
    VisumTransfer)

from visumtransfer.visum_tables import (
    Matrix,
    UserDefinedGroup,
    UserDefinedAttribute,
    Demandmodel,
    StructuralProp,
    Activity,
    PersonGroup,
    Activitypair,
    Activitychain,
    DemandStratum,
    TimeSeries,
    TimeSeriesItem,
    DemandTimeSeries,
    VisemTimeSeries,
    DemandSegment,
    TableDefinition,
    create_userdefined_table,
)

from visumtransfer.params import Params


class VisemDemandModel:
    """create a transfer file for a VisemModel"""

    def __init__(self,
                 modifications: str,
                 param_excel_fp: str):
        self.modifications = modifications
        self.params_excel_fp = param_excel_fp

    def create_transfer(self, params: Params, modification_number: int):

        dsegcodes = ['O'] # , 'AboA', 'AboJ', 'AboS']

        vt = VisumTransfer.new_transfer()

        tabledef = TableDefinition(mode='+')
        vt.tables['TabDefs'] = tabledef

        userdefgroups = UserDefinedGroup(mode='+')
        vt.tables['UserDefsGroups'] = userdefgroups

        userdef1 = UserDefinedAttribute(mode='')
        vt.tables['BenutzerdefinierteAttribute1'] = userdef1
        userdef2 = UserDefinedAttribute(mode='')

        tbl_pgrcat = self.add_pgr_categories(vt, tabledef, userdef1)
        vt.tables['PersongroupCategories'] = tbl_pgrcat

        model_code = 'VisemGGR'
        model_name = 'Visem Ziel- und Verkehrsmittelwahlmodell'
        self.add_demand_model(model_code, model_name, params.mode_set, vt)

        matrices = Matrix()

        pgr_summe = params.group_definitions.loc[
            (params.group_definitions['category'] == 'agegroup') &
            (params.group_definitions['id_in_category'] == -1),
            'code'].iloc[0]
        tbl_model, tbl_ca = self.add_params_persongrupmodel(
            tabledef,
            userdef1,
            pgr_summe=pgr_summe)
        vt.tables['ParamfilePersongroupmodel'] = tbl_model
        vt.tables['CarAvailabiliity'] = tbl_ca

        self.add_strukturgroessen(params.activities, model_code, vt)

        dsegs = self.add_nsegs_pkw_sv()
        vt.tables['DemandSegment'] = dsegs

        # Kenngrößenmatrizen
        self.add_skim_matrices(matrices, params, userdef1, dsegcodes)

        acts = self.add_activities(userdefgroups, userdef1, userdef2, matrices,
                                   params, model_code, vt)

        pg = self.add_persongroups(userdefgroups, userdef1, userdef2, matrices, acts,
                                   params, model_code, vt)

        ap = Activitypair()
        ap.create_tables(params.activitypairs, model=model_code)
        vt.tables['Activitypair'] = ap

        ak = Activitychain()
        ak.create_tables(params.trip_chain_rates, model=model_code)
        vt.tables['Activitychain'] = ak

        ns = DemandStratum()
        userdef1.add_data_attribute('DemandStratum',
                                     'MainActCode',
                                     valuetype='LongText',
                                     )
        userdef1.add_data_attribute('DemandStratum',
                                     'Mobilitaetsrate')
        userdef1.add_data_attribute('DemandStratum',
                                     'Tours',
                                     comment='Touren der DemandStratum')
        userdef1.add_data_attribute('DemandStratum',
                                     'Trips',
                                     comment='Wege der DemandStratum')
        userdef1.add_data_attribute('DemandStratum',
                                     'Tarifmatrix',
                                     valuetype='LongText',
                                     comment='Tarifmatrix der DemandStratum')

        gr_coeff = 'Koeffizienten'
        for m in params.mode_set.split(','):
            userdef1.add_data_attribute('Mainzone',
                                         f'CONST_ORIGIN_{m}',
                                         valuetype='Double',
                                         defaultvalue=0.0,
                                         comment=f'Kalibrierungsfaktor Oberbezirk Wohnort {m}',
                                         userdefinedgroupname=gr_coeff,
                                         )
            userdef1.add_data_attribute('Mainzone',
                                         f'CONST_DESTINATION_{m}',
                                         valuetype='Double',
                                         defaultvalue=0.0,
                                         comment=f'Kalibrierungsfaktor Oberbezirk Zielort {m}',
                                         userdefinedgroupname=gr_coeff,
                                         )
            userdef1.add_data_attribute('Persongroup',
                                         f'Factor_Cost_{m}',
                                         valuetype='Double',
                                         comment=f'Kostenfaktor {m}',
                                         userdefinedgroupname=gr_coeff,
                                         )
            formula = f'TableLookup(ACTIVITY Act, Act[CODE]=[MAIN_ACT], Act[Factor_Cost_{m}])'
            userdef1.add_formula_attribute('Persongroup',
                                          f'Factor_Cost_{m}_MainAct',
                                          formula=formula,
                                          valuetype='Double',
                                          comment=f'Kostenfaktor {m} der Hauptaktivität',
                                          userdefinedgroupname=gr_coeff,
                                          )
            userdef1.add_data_attribute('Persongroup',
                                         f'Factor_Time_{m}',
                                         valuetype='Double',
                                         comment=f'Zeitfaktor {m}',
                                         userdefinedgroupname=gr_coeff,
                                         )
            formula = f'TableLookup(ACTIVITY Act, Act[CODE]=[MAIN_ACT], Act[Factor_Time_{m}])'
            userdef1.add_formula_attribute('Persongroup',
                                          f'Factor_Time_{m}_MainAct',
                                          formula=formula,
                                          valuetype='Double',
                                          comment='Zeitfaktor {m} der Hauptaktivität',
                                          userdefinedgroupname=gr_coeff,
                                          )
        formula = 'TableLookup(ACTIVITY Act, Act[CODE]=[MAIN_ACT], Act[Tarifmatrix])'
        userdef1.add_formula_attribute('Persongroup',
                                      f'Tarifmatrix_MainAct',
                                      formula=formula,
                                      valuetype='LongText',
                                      comment='Tarifmatrix der Hauptaktivität',
                                      userdefinedgroupname=gr_coeff,
                                      )

        ns.create_tables_gd(personengruppe=pg,
                            activity=acts,
                            activitychain=ak,
                            model=model_code,
                            category='ZielVMWahl')
        ns.create_tables_gd(personengruppe=pg,
                            activity=acts,
                            activitychain=ak,
                            model=model_code,
                            category='ZielVMWahl_RSA')
        vt.tables['DemandStratum'] = ns

        # Nachfragematrizen
        #matrices.add_iv_demand(loadmatrix=1)
        #matrices.add_ov_demand(loadmatrix=1)
        matrices.add_other_demand_matrices(params, loadmatrix=0)
        matrices.add_commuter_matrices()

        # Erreichbarkeiten
        self.add_accessibility_matrices(matrices,
                                        params,
                                        userdefgroups,
                                        userdef2,
                                        model=model_code)

        # add matrices later
        vt.tables['Matrizen'] = matrices
        vt.tables['BenutzerdefinierteAttribute2'] = userdef2

        #  Skip adding logsum-Matrices
        if False:
            self.add_logsum_matrices(ak, ns, vt)

        self.add_ganglinien(pg, params, vt)

        fn = vt.get_modification(modification_number, self.modifications)
        vt.write(fn=fn)

    def add_skim_matrices(self,
                          matrices: Matrix,
                          params: Params,
                          userdef1: UserDefinedAttribute,
                          dsegcodes: DemandSegment):
        """add skim matrices"""
        matrices.set_category('General')
        matrices.add_data_matrix('Diagonal',
                                  category='General',
                                  matrixtype='Skim',
                                  loadmatrix=0)
        matrices.add_data_matrix('NoDiagonal',
                                  category='General',
                                  matrixtype='Skim',
                                  loadmatrix=0)
        matrices.add_ov_kg_matrices(params, userdef1, dsegcodes=dsegcodes)
        matrices.add_iv_kg_matrices(userdef1)

    def add_logsum_matrices(self,
                            ak: Activitychain,
                            ns: DemandStratum,
                            vt: VisumTransfer):
        """Add logsum-matrices"""
        matrices_logsum = Matrix()
        matrices_logsum.add_logsum_matrices(ns, ak)
        vt.tables['MatrizenLogsum'] = matrices_logsum

    def add_accessibility_matrices(self,
                                   matrices: Matrix,
                                   params: Params,
                                   userdefgroups: UserDefinedGroup,
                                   userdefined: UserDefinedAttribute,
                                   model: str,
                                   matrix_range: str = 'Logsums',
                                   ):
        """Add logsum matrices for Accessibility Calculation"""

        gr_acc = 'Erreichbarkeit'
        gr_popstruct = 'Bevölkerungsstruktur'
        userdefgroups.add(name=gr_acc, description='Erreichbarkeit')
        userdefgroups.add(name=gr_popstruct, description='Bevölkerungsstruktur')

        matrices.set_category(matrix_range)

        for idx, row in params.accessibilities.iterrows():

            ls_matname = row.matname_logsum
            matrices.add_data_matrix(
                ls_matname,
                category='Accessibility',
                matrixtype='Skim',
                dmodelcode=model,
                persongroupcode=row.persongroupcode,
                activitycode=row.activitycode)
            no = matrices.add_formula_matrix(
                row.matname_accessibility,
                category='Accessibility',
                matrixtype='Skim',
                dmodelcode=model,
                persongroupcode=row.persongroupcode,
                activitycode=row.activitycode,
                formula=f'EXP(Matrix([CODE] = "{ls_matname}")) * TO[{row.potential}]',
            )
            userdefined.add_formula_attribute('ZONE',
                                             row.zone_attribute,
                                             formula=f'LN([MATROWSUM({no})])',
                                             userdefinedgroupname=gr_acc)
        userdefined.add_formula_attribute('ZONE',
                                         'Anteil_Studis',
                                         formula='[NUMPERSONS(ST)]/([NUMPERSONS(ASUMME)])',
                                         userdefinedgroupname=gr_popstruct,
                                         )
        userdefined.add_formula_attribute('ZONE',
                                         'Anteil_Erwerbstaetige',
                                         formula='([NUMPERSONS(VZ)]+[NUMPERSONS(TZ)])/([NUMPERSONS(ASUMME)])',
                                         userdefinedgroupname=gr_popstruct,
                                         )

    def add_ganglinien(self,
                       pg: PersonGroup,
                       params: Params,
                       vt: VisumTransfer):
        """Add the Ganglinien"""
        gl = TimeSeries()
        gle = TimeSeriesItem()
        ngl = DemandTimeSeries()
        vgl = VisemTimeSeries()
        gl.create_tables(params.activitypairs,
                         params.time_series,
                         params.activitypair_time_series,
                         gle, ngl, vgl, pg)

        vt.tables['Ganglinie'] = gl
        vt.tables['Ganglinienelement'] = gle
        vt.tables['VisemGanglinien'] = vgl

    def add_persongroups(self,
                         userdefgroups: UserDefinedGroup,
                         userdef1: UserDefinedAttribute,
                         userdef2: UserDefinedAttribute,
                         matrices: Matrix,
                         acts: Activity,
                         params: Params,
                         model_code: str,
                         vt: VisumTransfer,
                         ) -> PersonGroup:
        """Create the Person Groups"""

        # add userdefined attributes for personsgroups
        pg = PersonGroup()
        pg._defaults['DEMANDMODELCODE'] = model_code
        vt.tables['PersonGroups'] = pg
        self.add_general_pgr_attributes(pg, userdef1, userdef2)

        modes = params.modes

        for _, mode in modes.iterrows():
            self.add_mode_specific_pgr_attributes(pg, mode, userdef1, userdef2)

        pg.add_df(params.group_definitions)
        # add the categories
        for pgr_category in params.group_definitions['CATEGORY'].unique():
            self.add_category(pgr_category, {}, vt)

        # create the groups for the RSA-Model
        categories = ['RSA', 'occupation', 'car_availability', 'Teilraum', 'Gesamt']
        category_generation = 'ErzeugungRSA'
        gd = pg.get_groups_destmode(categories, new_category=category_generation)
        pg.add_df(gd)

        categories = ['RSA', 'Pendler']
        gd = pg.get_groups_destmode(categories, new_category=category_generation)
        pg.add_df(gd)

        category = 'ZielVMWahl_RSA'
        #tc_categories = ['occupation', 'car_availability']
        attrs = {
            'Comment': 'Zielwahl für Randsummenabgleich',
            'ActivityMatrixPrefix': 'Pendlermatrix_',
            'ActivityMatrixOBBPrefix': 'Pendlermatrix_OBB_',
            'Prefix_GG': 'RSA_',
            'PersonGroupPrefix': 'Pgr_',
            'RSA': 1,
        }
        self.add_category(category, attrs, vt)
        tc_categories = ['occupation']
        pg.create_groups_destmode(params.groups_generation,
                                  params.trip_chain_rates_rsa,
                                  acts,
                                  model_code,
                                  tc_categories,
                                  category,
                                  category_generation,
                                  output_categories=['RSA'])
        tc_categories = ['Pendler']
        pg.create_groups_destmode(params.groups_generation,
                                  params.trip_chain_rates_rsa,
                                  acts,
                                  model_code,
                                  tc_categories,
                                  category,
                                  category_generation,
                                  output_categories=['RSA'])

        #  Create the groups for the Main Model
        category_generation = 'Erzeugung'
        categories = ['occupation', 'car_availability', 'Teilraum', 'Gesamt']
        gd = pg.get_groups_destmode(categories, new_category=category_generation)
        pg.add_df(gd)
        categories = ['Pendler']
        gd = pg.get_groups_destmode(categories, new_category=category_generation)
        pg.add_df(gd)

        category = 'ZielVMWahl'
        attrs = {
            'Comment': 'Ziel- und Verkehrsmittelwahl mit Visem',
            'ActivityMatrixPrefix': 'Activity_',
            'ActivityMatrixOBBPrefix': 'Activity_OBB_',
            'PersonGroupPrefix': 'Pgr_',
        }
        self.add_category(category, attrs, vt)
        categories = ['occupation', 'car_availability', 'Teilraum', 'Gesamt']
        tc_categories = ['occupation']
        pg.create_groups_destmode(params.groups_generation,
                                  params.trip_chain_rates,
                                  acts,
                                  model_code,
                                  tc_categories,
                                  category,
                                  category_generation,
                                  output_categories=categories)
        categories = ['Pendler']
        tc_categories = ['Pendler']
        pg.create_groups_destmode(params.groups_generation,
                                  params.trip_chain_rates,
                                  acts,
                                  model_code,
                                  tc_categories,
                                  category,
                                  category_generation,
                                  output_categories=categories)

        # Create the Dataframe
        pg.create_df_from_group_list()

        pg.add_calibration_matrices_and_attributes(modes, matrices)
        return pg

    def add_activities(self,
                       userdefgroups: UserDefinedGroup,
                       userdef1: UserDefinedAttribute,
                       userdef2: UserDefinedAttribute,
                       matrices: Matrix,
                       params: Params,
                       model_code: str,
                       vt: VisumTransfer,
                       ) -> Activity:
        """Add the activities and create the related tables"""
        # Aktivitäten
        acts = Activity()
        userdef1.add_data_attribute('Activity', 'RSA', valuetype='Bool')
        userdef1.add_data_attribute('Activity', 'Autocalibrate',
                                     valuetype='Bool')
        userdef1.add_data_attribute('Activity', 'Composite_Activities',
                                     valuetype='Text')
        userdef1.add_data_attribute('Activity', 'Activityset',
                                     valuetype='Text')
        userdef1.add_data_attribute('Activity',
                                     code='CalcDestMode',
                                     name='CalculateDestinationAndModeChoice',
                                     valuetype='Bool')
        # spezifische Attribute für die Zielwahl
        userdef1.add_data_attribute('Activity', 'LS',
                                     defaultvalue=1.0,
                                     comment='LogSum-Parameter der Aktivität, '
                                     'berechnet als Multiplikation der LS_Factors '
                                     'aller zugehörigen Aktivitäten')
        # spezifische Attribute für die Zielwahl
        userdef1.add_data_attribute('Activity', 'BASE_LS',
                                     defaultvalue=1.0,
                                     comment='Basis-LogSum-Faktor der Aktivität, '
                                     'wird mit anderen Faktoren multipliziert')
        # spezifische Attribute für die Zielwahl
        userdef1.add_data_attribute('Activity', 'KF_BASE_LS',
                                     defaultvalue=1.0,
                                     comment='Korrekturfaktor für LogSum der Aktivität, '
                                     'während Kalibrierung')
        # spezifische Attribute für die Verkehrsmittelwahl
        userdef1.add_data_attribute(
            objid='ACTIVITY',
            name='ZIELWAHL_FUNKTION_MATRIXCODES',
            valuetype='LongText',
            comment='Codes der Matrizen, die in die Zielwahl-Funktion einfliessen',
        )
        userdef1.add_data_attribute(
            objid='ACTIVITY',
            name='TARIFMATRIX',
            valuetype='LongText',
            comment='Name einer speziellen Tarifmatrix, '
            'die bei dieser Hauptaktivität verwendet werden soll',
        )

        acts.create_tables(params.activities, model=model_code, suffix='')
        acts.add_benutzerdefinierte_attribute(userdef2)
        acts.add_output_matrices(matrices, userdefgroups, userdef2)
        acts.add_modal_split(userdefgroups, userdef2, matrices, params.modes)
        acts.add_balancing_output_matrices(matrices, userdefgroups, userdef2, loadmatrix=0)
        acts.add_parkzone_attrs(userdefgroups, userdef2)
        acts.add_parking_matrices(matrices)
        acts.add_pjt_matrices(matrices)
        acts.add_kf_logsum(userdefgroups, userdef2)
        vt.tables['Aktivitaet'] = acts
        return acts

    def add_strukturgroessen(self,
                             activities: pd.DataFrame,
                             model_code: str,
                             vt: VisumTransfer):
        """Add Table Strukturgrößen"""
        sg = StructuralProp()
        sg.create_tables(activities, model=model_code, suffix='')
        vt.tables['Strukturgr'] = sg

    def add_demand_model(self,
                         model_code: str,
                         model_name: str,
                         mode_set: str,
                         v: VisumTransfer):
        """add the demand model with code and name and mode_set"""
        model = Demandmodel()
        model.add(code=model_code,
                  name=model_name,
                  type='VISEM',
                  modeset=mode_set)
        v.tables['Nachfragemodell'] = model

    def add_pgr_categories(self,
                           v: VisumTransfer,
                           tabledef: TableDefinition,
                           userdef1: UserDefinedAttribute):
        """Add userdefined net attribute"""

        TBL_pgrcat = create_userdefined_table(
            name='PersonGroupCategories',
            cols_types={'ActivityMatrixOBBPrefix': 'LongText',
                        'ActivityMatrixPrefix': 'LongText',
                        'Comment': 'LongText',
                        'name': 'LongText',
                        'PersonGroupPrefix': 'LongText',
                        'Prefix_GG': 'LongText',
                        'RSA': 'Bool',
                        },
            group='PersonGroupModel',
            comment='Attribute der PERSONGROUPn-Kategorien',
            tabledef=tabledef,
            userdef=userdef1,
        )

        tbl_pgrcat = TBL_pgrcat(mode='')
        return tbl_pgrcat

    def add_category(self,
                     category: str,
                     attrs: dict,
                     vt: VisumTransfer,
                     category_attribute: str = 'PgrCategories'):
        """
        Add category to the net-attribute category_attribute
        and set the attributes
        """
        pgrcat = vt.tables['PersongroupCategories']
        attrs_lower = {k.lower(): v for k, v in attrs.items()}
        pgrcat.add(name=category, **attrs_lower)

    def add_general_pgr_attributes(self,
                                   pg: PersonGroup,
                                   userdef1: UserDefinedAttribute,
                                   userdef2: UserDefinedAttribute):
        """Add general Attributes for the Persongrups"""
        gr_trips = 'Wege'
        gr_dist = 'Distanz'

        userdef1.add_data_attribute('PERSONGROUP', 'CATEGORY', valuetype='Text',
                                     comment='Kategorie der Personengruppe')
        userdef1.add_data_attribute(
            'PERSONGROUP', 'CODEPART', valuetype='Text',
            comment='Code-Bestandteil der Zusammengesetzten Personengruppen'
        )
        userdef1.add_data_attribute(
            'PERSONGROUP', 'NAMEPART', valuetype='Text',
            comment='Namens-Bestandteil der Zusammengesetzten Personengruppen'
        )
        userdef1.add_data_attribute(
            'PERSONGROUP', 'CALIBRATION_HIERARCHY', valuetype='Int',
            comment='Hierarchie bei der Kalibrierung des Modal Splits'
            'Der Modal Split der höchsten Hierarchiestufe wird zuletzt kalibriert'
            'und wird damit am genauesten getroffen.'
        )
        userdef1.add_data_attribute(
            'PERSONGROUP', 'ID_IN_CATEGORY', valuetype='Int',
            comment='Fortlaufende id innerhalb einer Kategorie')
        userdef1.add_data_attribute(
            'PERSONGROUP', 'GROUPS_CONSTANTS', valuetype='Text',
            comment='Komma-getrennte Liste der Obergruppen, deren '
            'verkehrsmittelspezifische Konstante in die Nutzenfunktion einer '
            'Obergruppe einbezogen werden soll.'
        )
        userdef1.add_data_attribute(
            'PERSONGROUP', 'GROUPS_OUTPUT', valuetype='Text',
            comment='Komma-getrennte Liste der Obergruppen, in die die Berechnungs-'
            'Ergebnisse der Gruppe einfließen soll.'
        )
        userdef1.add_data_attribute(
            'PERSONGROUP', 'GROUP_GENERATION', valuetype='Text',
            comment='Code der Personengruppe für das Erzeugungsmodell'
        )
        userdef1.add_data_attribute(
            'PERSONGROUP', 'MAIN_ACT', valuetype='Text',
            comment='Hauptaktivität der Personengruppe'
        )
        userdef1.add_data_attribute(
            'PERSONGROUP', 'Persons', valuetype='Double',
            comment='Personen in Personengruppe'
        )
        userdef1.add_data_attribute(
            'PERSONGROUP', 'Faktor_Erwerbstaetigkeit', valuetype='Double',
            comment='Anteil der Erwerbstätigen an der Personengruppe',
        )
        userdef1.add_formula_attribute(
            'PERSONGROUP', 'Erwerbstaetige', valuetype='Double',
            formula='[PERSONS] * [FAKTOR_ERWERBSTAETIGKEIT]',
          comment='Erwerbstätige Personen',
        )
        userdef1.add_data_attribute(
            'PERSONGROUP', 'Tarifmatrix', valuetype='LongText',
          comment='spezielle Tarifmatrix der Personengruppe',
        )
        userdef1.add_data_attribute(
            objid='PERSONGROUP',
            name='ZIELWAHL_FUNKTION_MATRIXCODES',
            valuetype='LongText',
          comment='Codes der Matrizen, die in die Zielwahl-Funktion einfliessen',
        )
        pg.add_cols(['CATEGORY', 'CODEPART', 'NAMEPART',
                     'CALIBRATION_HIERARCHY', 'ID_IN_CATEGORY',
                     'GROUPS_CONSTANTS', 'GROUPS_OUTPUT', 'GROUP_GENERATION',
                     'MAIN_ACT', 'PERSONS', 'FAKTOR_ERWERBSTAETIGKEIT', 'TARIFMATRIX',
                     'ZIELWAHL_FUNKTION_MATRIXCODES'])

        # Wege Gesamt und Verkehrsleistung der Gruppe
        formula = f'TableLookup(MATRIX Mat: Mat[CODE]="Pgr_"+[CODE]: Mat[SUM])'
        userdef2.add_formula_attribute(
            objid='PERSONGROUP',
            name=f'Trips',
            formula=formula,
          comment=f'Gesamtzahl der Wege der Gruppe',
            userdefinedgroupname=gr_trips,
        )
        formula = f'TableLookup(MATRIX Mat: Mat[CODE]="VL_Pgr_"+[CODE]: Mat[SUM])'
        userdef2.add_formula_attribute(
            objid='PERSONGROUP',
            name=f'Km',
            formula=formula,
          comment=f'Gesamte Verkehrsleistung der Gruppe',
            userdefinedgroupname=gr_dist,
        )
        # Mittlere Wegelänge
        userdef2.add_formula_attribute(
            objid='PERSONGROUP',
            name=f'MeanTripLength',
            formula='[Km]/[Trips]',
          comment=f'Mittlere Wegelänge [km]',
            userdefinedgroupname=gr_dist,
        )
        # Wege und Verkehrsleistung pro Person
        userdef2.add_formula_attribute(
            objid='PERSONGROUP',
            name=f'Trips_per_Person',
            formula='[Trips]/[Persons]',
          comment=f'Wege Pro Person',
            userdefinedgroupname=gr_trips,
        )
        userdef2.add_formula_attribute(
            objid='PERSONGROUP',
            name=f'Km_per_Person',
            formula='[Km]/[Persons]',
          comment=f'Wege Pro Person',
            userdefinedgroupname=gr_dist,
        )

    def add_mode_specific_pgr_attributes(self,
                                         pg: PersonGroup,
                                         mode: pd.Series,
                                         userdef1: UserDefinedAttribute,
                                         userdef2: UserDefinedAttribute):
        """Add mode-specific Attributes for the Persongrups"""
        gr_coeff = 'Koeffizienten'
        gr_ms = 'Modal Split'
        gr_trips = 'Wege'
        gr_dist = 'Distanz'

        m = mode.code
        userdef1.add_data_attribute(
            'PERSONGROUP', f'BASECONST_{m}', valuetype='Double',
            comment=f'Konstante für Verkehrsmittel {mode.name}',
            userdefinedgroupname=gr_coeff,
        )
        userdef1.add_data_attribute(
            'PERSONGROUP', f'CONST_{m}', valuetype='Double',
            comment=f'Konstante für Verkehrsmittel {mode.name}',
            userdefinedgroupname=gr_coeff,
        )
        userdef1.add_data_attribute(
            'PERSONGROUP', f'TARGET_MS_{m}', valuetype='Double',
            comment=f'Ziel-ModalSplit für Verkehrsmittel {mode.name}',
            userdefinedgroupname=gr_ms,
        )
        userdef1.add_data_attribute(
            objid='PERSONGROUP',
            name=f'KF_CONST_{m}',
            defaultvalue=0,
            comment=f'Korrektur der Konstante bei Kalibrierung für {mode.name}',
            userdefinedgroupname=gr_coeff,
        )

        pg.add_cols([f'BASECONST_{m}', f'CONST_{m}', f'TARGET_MS_{m}', f'KF_CONST_{m}'])

        # Trips by Mode und Modal Split of the Group
        formula = f'TableLookup(MATRIX Mat: Mat[CODE]="Pgr_"+[CODE]+"_{m}": Mat[SUM])'
        userdef2.add_formula_attribute(
            objid='PERSONGROUP',
            name=f'Trips_{m}',
            formula=formula,
            comment=f'Gesamtzahl der Wege mit Verkehrsmittel {mode.name}',
            userdefinedgroupname=gr_trips,
        )
        formula = f'TableLookup(MATRIX Mat: Mat[CODE]="VL_Pgr_"+[CODE]+"_{m}": Mat[SUM])'
        userdef2.add_formula_attribute(
            objid='PERSONGROUP',
            name=f'Km_{m}',
            formula=formula,
            comment=f'Verkehrsleistung mit Verkehrsmittel {mode.name} der Gruppe',
            userdefinedgroupname=gr_dist,
        )
        # Modal Split der Gruppe
        userdef2.add_formula_attribute(
            objid='PERSONGROUP',
            name=f'MS_{m}',
            formula=f'[Trips_{m}] / [Trips]',
            comment=f'Modal Split-Anteil {mode.name}',
            userdefinedgroupname=gr_ms,
        )
        # Mittlere Wegelänge
        userdef2.add_formula_attribute(
            objid='PERSONGROUP',
            name=f'MeanTripLength_{m}',
            formula=f'[Km_{m}]/[Trips_{m}]',
            comment=f'Mittlere Wegelänge {mode.name}',
            userdefinedgroupname=gr_dist,
        )
        # Wege und Verkehrsleistung pro Person
        userdef2.add_formula_attribute(
            objid='PERSONGROUP',
            name=f'Trips_Per_Person_{m}',
            formula=f'[Trips_{m}] / [Persons]',
            comment=f'Modal Split-Anteil {mode.name}',
            userdefinedgroupname=gr_trips,
        )
        userdef2.add_formula_attribute(
            objid='PERSONGROUP',
            name=f'Km_Per_Person_{m}',
            formula=f'[Km_{m}] / [Persons]',
            comment=f'Km pro Person {mode.name}',
            userdefinedgroupname=gr_dist,
        )

    def add_params_persongrupmodel(self,
                                   tabledef: TableDefinition,
                                   userdef1: UserDefinedAttribute,
                                   pgr_summe: str = 'ASumme'):

        userdef1.add_data_attribute('Zone', 'MODELLIERUNGSRAUM', valuetype='Int',
                                     userdefinedgroupname='Gebietszuordnung')
        userdef1.add_data_attribute('Zone', 'OBB_OCCUPATION', valuetype='Int',
                                     userdefinedgroupname='Gebietszuordnung')
        userdef1.add_data_attribute('Zone', 'OBB_CARS', valuetype='Int',
                                     userdefinedgroupname='Gebietszuordnung')

        TBL_model = create_userdefined_table(
            name='ParamFilePersonGroupModel',
            cols_types={'key': 'LongText', 'value': 'LongText', },
            group='PersonGroupModel',
            comment='Beschreibung der Excel-Datei für das Personengruppen-Modell',
            tabledef=tabledef,
            userdef=userdef1,
        )

        tbl_model = TBL_model(mode='')
        params_pgrmodel = dict(
            excel_filename="ParamsPersongroupModel.xlsx",
            excel_folder='',
            sn_occupation='Taetigkeit_Long',
            sn_caravailability='Pkwverf_Long',
            sn_lab_occupation='lab_taetigkeit',
            sn_lab_caravailability='lab_pkwverf',
            sn_lab_gebiet='lab_gebiet',
        )
        for k, v in params_pgrmodel.items():
            tbl_model.add(key=k, value=v)

        # Attribute für Motorisierung
        userdef1.add_data_attribute('Zone', 'Pkw_Personengruppen',
                                     userdefinedgroupname='Bevölkerungsstruktur')
        formula = f'[Pkw_Personengruppen] / [NUMPERSONS({pgr_summe})] * 1000'
        userdef1.add_formula_attribute('Zone', 'Motorisierung', formula=formula,
                                      userdefinedgroupname='Bevölkerungsstruktur')

        comment = 'Pkw nach Pkw-Verfügbarkeit'

        TBL_model = create_userdefined_table(
            name='Cars_By_Caravailability',
            cols_types={'key': 'LongText', 'value': 'Double', },
            group='PersonGroupModel',
            comment=comment,
            tabledef=tabledef,
            userdef=userdef1,
        )
        tbl_ca = TBL_model('')
        pgr_ca = params.group_definitions.loc[
            params.group_definitions['category'] == 'car_availability',
            ['code', 'factor_pkwverf_anzpkw']]
        for idx, row in pgr_ca.iterrows():
            tbl_ca.add(key=row.code, value=row.factor_pkwverf_anzpkw)

        # OBB-Attribute für Kalibrierung Erwerbstätigkeit und Motorisierung
        userdef1.add_data_attribute('Mainzone', 'BF_OBB_ERWERBST', defaultvalue=0.0)
        userdef1.add_data_attribute('Mainzone', 'BF_OBB_PKW', defaultvalue=0.0)
        userdef1.add_formula_attribute('Mainzone', 'EINWOHNER',
                                      formula=r'[SUM:ZONES\ZP_EINWOHNER]')
        userdef1.add_formula_attribute('Mainzone', 'SGB2_EMPFAENGER',
                                      formula='[ARBEITSLOSE]*2.5')
        userdef1.add_formula_attribute('Mainzone', 'MODELLIERUNGSRAUM',
                                      formula=r'[SUM:ZONES\MODELLIERUNGSRAUM]>0')
        userdef1.add_formula_attribute('Mainzone', 'CALIBRATION_ERWERBSTAETIGKEIT',
                                      formula=r'[SUM:ZONES\MODELLIERUNGSRAUM]>0')
        userdef1.add_formula_attribute('Mainzone', 'CALIBRATION_PKWVERFUEGBARKEIT',
                                      formula=r'[SUM:ZONES\MODELLIERUNGSRAUM]>0')

        return tbl_model, tbl_ca

    def write_modification_iv_matrices(self, modification_number: int):
        v = VisumTransfer.new_transfer()

        matrices = Matrix()
        matrices.add_iv_demand()
        v.tables['Matrizen'] = matrices
        v.write(fn=v.get_modification(modification_number, self.modifications))

    def write_modification_ov_matrices(self, modification_number: int):
        v = VisumTransfer.new_transfer()

        matrices = Matrix()
        matrices.add_ov_demand()
        v.tables['Matrizen'] = matrices
        v.write(fn=v.get_modification(modification_number, self.modifications))

    def add_nsegs_pkw_sv(self) -> DemandSegment:
        """add nsegs"""
        # DemandSegmente
        nseg = DemandSegment()
        nseg.add(code='SV', name='Schwerverkehr',mode='L')
        nseg.add(code='PG', name='Kfz bis 3,5 to',mode='P')
        return nseg

    def add_nsegs_userdefined(self, modification_no: int, dsegcodes_put: List[str]):
        vt = VisumTransfer.new_transfer()
        userdef0 = UserDefinedAttribute()
        vt.tables['BenutzerdefinierteAttribute0'] = userdef0

        # Matrizen
        userdef0.add_data_attribute('Matrix', 'INITMATRIX', valuetype='Bool')
        userdef0.add_data_attribute('Matrix', 'LOADMATRIX', valuetype='Bool')
        userdef0.add_data_attribute('Matrix', 'SAVEMATRIX', valuetype='Bool')
        userdef0.add_data_attribute('Matrix', 'MATRIXFOLDER', valuetype='Text')
        userdef0.add_data_attribute('Matrix', 'CALIBRATIONCODE', valuetype='Text')
        userdef0.add_data_attribute('Matrix', 'CATEGORY', valuetype='Text')
        userdef0.add_data_attribute('Matrix', 'OBB_MATRIX_REF', valuetype='LongText')

        # Netzattribute
        userdef0.add_data_attribute('Network', 'COST_PER_KM_PKW',
                                     defaultvalue=0.15)
        userdef0.add_data_attribute('Network', 'MINUS_ONE', defaultvalue=-1)

        # TSys-Attribute
        userdef0.add_data_attribute('TSys', 'VSYS_TRAVELTIME_BONUS', defaultvalue=1.0)
        userdef0.add_data_attribute('TSys', 'VSYS_MALUS', defaultvalue=6.0)

        # Mode-Attribute
        userdef0.add_data_attribute('Mode', 'BASEMODE', valuetype='Bool', defaultvalue=0)
        userdef0.add_data_attribute('Mode', 'COEFF_PARKING', defaultvalue=0.0)
        userdef0.add_data_attribute('Mode', 'COEFF_TRAVELTIME', defaultvalue=0.0)
        userdef0.add_data_attribute('Mode', 'COEFF_TRAVEL_COST', defaultvalue=0.0)
        userdef0.add_data_attribute('Mode', 'COST_PER_KM', defaultvalue=0.0)

        mode_lkw = 'LKW_XL'
        # DemandSegmente
        nseg = DemandSegment()
        vt.tables['DemandSegment'] = nseg

        nseg.add(code='OFern', name='ÖV Fernverkehr', mode='O')
        nseg.add(code='B_P', name='Pkw-Wirtschaftsverkehr', mode='P')
        nseg.add(code='B_Li', name='Lieferfahrzeug', mode='P')
        nseg.add(code='B_L1', name='Lkw bis 12 to', mode=mode_lkw)
        nseg.add(code='B_L2', name='Lkw 12-40 to', mode=mode_lkw)
        nseg.add(code='LkwFern', name='Lkw Fernverkehr',mode=mode_lkw)
        nseg.add(code='PkwFern', name='Pkw Fernverkehr',mode='P')
        nseg.add(code='SV', name='Schwerverkehr',modes=mode_lkw)
        nseg.add(code='PG', name='Kfz bis 3,5 to',mode='P')

        for dsegcode in dsegcodes_put:
            nseg.add(code=dsegcode,modes='O')

        fn = vt.get_modification(modification_no, self.modifications)
        vt.write(fn=fn)

    def create_transfer_target_values(self, params: Params, modification_no: int):

        cols = [f'TARGET_MS_{mode.code}' for _, mode in params.modes.iterrows()]
        v = VisumTransfer.new_transfer()

        # Personengruppenspezifische Zielwerte Modal Split
        gd = params.group_definitions.set_index('CODE')
        gd = gd[cols]
        gd = gd.loc[gd.any(axis=1)]
        pg = PersonGroup(mode='*')
        pg.df = gd
        v.tables['Personengruppe'] = pg

        # Aktivitätenspezifische Zielwerte Modal Split
        va = params.validation_activities.set_index('code')
        va = va.loc[va['in_model'] == 1]
        va = va[cols + ['Target_MeanTripDistance']]
        va = va.loc[va.any(axis=1)]
        ac = Activity(mode='*')
        ac.df = va
        v.tables['Aktivitaet'] = ac

        #  Zielwerte Mittlere Wegelängen Aktivitäten

        fn = v.get_modification(modification_no, self.modifications)
        v.write(fn=fn)

    def create_transfer_constants(self, params: Params, modification_no: int):
        cols = [f'BASECONST_{mode.code}' for _, mode in params.modes.iterrows()]

        v = VisumTransfer.new_transfer()

        # Personengruppenspezifische Konstanten
        gd = params.group_definitions.set_index('CODE')
        gd = gd[cols]
        gd = gd.loc[gd.any(axis=1)]
        pg = PersonGroup(mode='*')
        pg.df = gd
        v.tables['Personengruppe'] = pg

        # Aktivitätenspezifische Konstanten
        va = params.validation_activities.set_index('code')
        va = va.loc[va['in_model'] == 1]
        va = va[cols]
        va = va.loc[va.any(axis=1)]
        ac = Activity(mode='*')
        ac.df = va
        v.tables['Aktivitaet'] = ac

        #  Logsum-Parameter
        acts = params.activities.set_index('code')
        acts = acts[['BASE_LS']]
        acts = acts.loc[acts.any(axis=1)]
        ac_ls = Activity(mode='*')
        ac_ls.df = acts
        v.tables['Aktivitaet_Logsum'] = ac_ls

        fn = v.get_modification(modification_no, self.modifications)
        v.write(fn=fn)

    def get_params(self, param_excel_fp: str) -> Params:
        return Params(param_excel_fp)


if __name__ == '__main__':
    argpase = ArgumentParser()
    argpase.add_argument('--infolder', type=str, default=r'D:\GGR\KS\55 Nachfragemodell')
    argpase.add_argument('--param_excel_fp', type=str, default='params_long_2023_NVV.xlsx')
    argpase.add_argument('--visum_folder', type=str, default=r'D:\GGR\KS\55 Nachfragemodell')
    argpase.add_argument('--mod_number', type=int, default=2)
    options = argpase.parse_args()

    param_excel_fp = os.path.join(options.infolder, options.param_excel_fp)
    modifications = os.path.join(options.visum_folder, 'Modifications')
    shared_data = os.path.join(options.visum_folder, 'SharedData')

    dm = VisemDemandModel(modifications,
                          param_excel_fp,
                          )

    params = dm.get_params(param_excel_fp)
    #dm.add_nsegs_userdefined(modification_no=5, dsegcodes_put=['O'])
    dm.create_transfer(params, modification_number=options.mod_number)
    #dm.create_transfer_constants(params, modification_no=7)
    #dm.create_transfer_target_values(params, modification_no=8)
    #dm.write_modification_iv_matrices(modification_number=9)
    #dm.write_modification_ov_matrices(modification_number=10)
