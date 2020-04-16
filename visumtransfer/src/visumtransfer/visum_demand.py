# -*- coding: utf-8 -*-


import os
from argparse import ArgumentParser

from visumtransfer.visum_table import (
    VisumTransfer)

from visumtransfer.visum_tables import (
    Matrix,
    BenutzerdefiniertesAttribut,
    Nachfragemodell,
    Strukturgr,
    Aktivitaet,
    Personengruppe,
    Aktivitaetenpaar,
    Aktivitaetenkette,
    Nachfrageschicht,
    Verkehrssystem,
    Ganglinie,
    Ganglinienelement,
    Nachfrageganglinie,
    VisemGanglinie,
    Nachfragesegment
)

from visumtransfer.params import Params


class VisemDemandModel:
    """create a transfer file for a VisemModel"""
    def __init__(self,
                 modifications: str,
                 param_excel_fp: str):
        self.modifications = modifications
        self.params_excel_fp = param_excel_fp

    def create_transfer_rsa(self, modification_number: int):
        v = VisumTransfer.new_transfer()
        params = Params(param_excel_fp)

        # Nachfragemodell
        m = Nachfragemodell()
        model_code = 'VisemRSA'
        m.add_model(params, code=model_code,
                    name='Visem-Modell zum Randsummenabgleich')
        v.tables['Nachfragemodell'] = m

        # Strukturgrößen
        sg = Strukturgr()
        sg.create_tables(params.activities_rsa, model=model_code, suffix='')
        v.tables['Strukturgr'] = sg

        # Aktivitäten
        ac = Aktivitaet()
        ac.create_tables(params.activities_rsa, model=model_code, suffix='')
        v.tables['Aktivitaet'] = ac

        # Personengruppen
        pgd = Personengruppe()
        pgd.create_groups_rsa(params.gd_rsa,
                              params.trip_chain_rates_rsa,
                              model_code=model_code)
        v.tables['PersonGroupsDestModechoice'] = pgd

        # Aktivitätenpaar
        ap = Aktivitaetenpaar()
        ap.create_tables(params.activitypairs_rsa, model=model_code)
        v.tables['Aktivitaetenpaar'] = ap

        ak = Aktivitaetenkette()
        ak.create_tables(params.trip_chain_rates_rsa, model=model_code)
        v.tables['Aktivitaetenkette'] = ak

        ns = Nachfrageschicht()
        ns.create_tables_gd(personengruppe=pgd,
                            model=model_code)
        v.tables['Nachfrageschicht'] = ns
        # write to transfer file
        fn = v.get_modification(modification_number, self.modifications)
        v.write(fn=fn)


    def create_transfer(self, modification_number: int):

        v = VisumTransfer.new_transfer()

        # use the data from the excel-file
        params = Params(param_excel_fp)

        userdefined1 = BenutzerdefiniertesAttribut()
        v.tables['BenutzerdefinierteAttribute1'] = userdefined1
        userdefined2 = BenutzerdefiniertesAttribut()

        matrices = Matrix()

        m = Nachfragemodell()
        m.add_model(params, code='VisemGeneration', name='Visem-Erzeugungsmodell')
        model_code = 'VisemT'
        m.add_model(params, code=model_code,
                    name='Visem Ziel- und Verkehrsmittelwahlmodell')
        v.tables['Nachfragemodell'] = m

        sg = Strukturgr()
        sg.create_tables(params.activities, model=model_code, suffix='')
        v.tables['Strukturgr'] = sg

        ac = Aktivitaet()
        userdefined1.add_daten_attribute('Aktivitaet', 'RSA', datentyp='Bool')
        userdefined1.add_daten_attribute('Aktivitaet', 'Base_Code',
                                         datentyp='Text')
        userdefined1.add_daten_attribute('Aktivitaet', 'Autocalibrate',
                                         datentyp='Bool')
        userdefined1.add_daten_attribute('Aktivitaet', 'Composite_Activities',
                                         datentyp='Text')
        userdefined1.add_daten_attribute('Aktivitaet', 'Aktivitaetset',
                                         datentyp='Text')
        userdefined1.add_daten_attribute('Aktivitaet',
                                         code='CalcDestMode',
                                         name='CalculateDestinationAndModeChoice',
                                         datentyp='Bool')

        ac.create_tables(params.activities, model=model_code, suffix='')
        ac.add_benutzerdefinierte_attribute(userdefined2)
        ac.add_net_activity_ticket_attributes(userdefined2)
        ac.add_output_matrices(matrices, userdefined2)
        ac.add_modal_split(userdefined2, matrices, params)
        ac.add_balancing_output_matrices(matrices, userdefined2, loadmatrix=0)
        ac.add_parking_matrices(matrices)
        ac.add_pjt_matrices(matrices)
        ac.add_kf_logsum(userdefined2)
        v.tables['Aktivitaet'] = ac

        userdefined1.add_daten_attribute('Personengruppe', 'ACTCHAIN',
                                         datentyp='Text')
        userdefined1.add_daten_attribute('Personengruppe', 'CAR_AVAILABILITY',
                                         datentyp='Text')
        userdefined1.add_daten_attribute('Personengruppe', 'GROUPDESTMODE',
                                         datentyp='Text')
        userdefined1.add_daten_attribute('Personengruppe', 'OCCUPATION',
                                         datentyp='Text')
        userdefined1.add_daten_attribute('Personengruppe', 'VOTT')
        pgg = Personengruppe()
        pgg.create_groups_generation(params)
        pgg.create_table()
        v.tables['PersonGroupsGeneration'] = pgg

        pgd = Personengruppe()
        pgd.create_groups_destmode(params, ac)
        pgd.create_table()
        pgd.add_calibration_matrices_and_attributes(params, matrices, userdefined2)
        v.tables['PersonGroupsDestModechoice'] = pgd

        ap = Aktivitaetenpaar()
        ap.create_tables(params.activitypairs, model=model_code, suffix='')
        v.tables['Aktivitaetenpaar'] = ap

        ak = Aktivitaetenkette()
        ak.create_tables(params.trip_chain_rates, model=model_code, suffix='')
        v.tables['Aktivitaetenkette'] = ak

        ns = Nachfrageschicht()
        ns.create_tables_gd(personengruppe=pgd,
                            model=model_code)
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
        self.define_vsys_fv_preference(vsys, userdefined2)

        # add matrices later
        v.tables['Matrizen'] = matrices
        v.tables['BenutzerdefinierteAttribute2'] = userdefined2
        v.tables['Verkehrssysteme'] = vsys

        #matrices_logsum = Matrix()
        #userdefined2.add_logsum_kf(userdefined2)
        #matrices_logsum.add_logsum_matrices(ns, ak)
        #v.tables['MatrizenLogsum'] = matrices_logsum

        gl = Ganglinie()
        gle = Ganglinienelement()
        ngl = Nachfrageganglinie()
        vgl = VisemGanglinie()
        gl.create_tables(params, gle, ngl, vgl, pgd)

        v.tables['Ganglinie'] = gl
        v.tables['Ganglinienelement'] = gle
        v.tables['VisemGanglinien'] = vgl

        fn = v.get_modification(modification_number, self.modifications)
        v.write(fn=fn)

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
        v.write(fn=v.get_modification(self.modifications, modification_number))


    def add_nsegs_userdefined(self, modification_no: int):
        v = VisumTransfer.new_transfer()
        userdefined0 = BenutzerdefiniertesAttribut()
        v.tables['BenutzerdefinierteAttribute0'] = userdefined0

        # Matrizen
        userdefined0.add_daten_attribute('Matrix', 'INITMATRIX', datentyp='Bool')
        userdefined0.add_daten_attribute('Matrix', 'LOADMATRIX', datentyp='Bool')
        userdefined0.add_daten_attribute('Matrix', 'SAVEMATRIX', datentyp='Bool')
        userdefined0.add_daten_attribute('Matrix', 'MATRIXFOLDER', datentyp='Text')
        userdefined0.add_daten_attribute('Matrix', 'CALIBRATIONCODE', datentyp='Text')
        userdefined0.add_daten_attribute('Matrix', 'CATEGORY', datentyp='Text')

        # Netzattribute
        userdefined0.add_daten_attribute('Netz', 'COST_PER_KM_PKW',
                                         standardwert=0.15)
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


        mode_lkw = 'X'
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
                              modus=mode_lkw))
        nseg.add_row(nseg.Row(code='B_L2', name='Lkw 12-40 to',
                              modus=mode_lkw))
        nseg.add_row(nseg.Row(code='LkwFern', name='Lkw Fernverkehr',
                              modus=mode_lkw))
        nseg.add_row(nseg.Row(code='PkwFern', name='Pkw Fernverkehr',
                              modus='P'))
        nseg.add_row(nseg.Row(code='SV', name='Schwerverkehr',
                              modus=mode_lkw))
        nseg.add_row(nseg.Row(code='PG', name='Kfz bis 3,5 to',
                              modus='P'))

        fn = v.get_modification(modification_no, self.modifications)
        v.write(fn=fn)


    def define_vsys_fv_preference(self,
                                  vsys: Verkehrssystem,
                                  userdefined2: BenutzerdefiniertesAttribut):
        #userdefined2.add_daten_attribute('VSYS', 'VSYS_FV_PREFERENCE', standardwert=1)
        vsys.add_cols(['VSYS_FV_PREFERENCE'])
        # row = vsys.Row(code='FAE', typ='OV', vsys_fv_preference=0.2)
        # vsys.add_row(row)
        row = vsys.Row(code='S', typ='OV', vsys_fv_preference=0.5)
        vsys.add_row(row)

if __name__ == '__main__':
    argpase = ArgumentParser()
    argpase.add_argument('--infolder', type=str)
    argpase.add_argument('--param_excel_fp', type=str, default='tdm_params.xlsx')
    argpase.add_argument('--visum_folder', type=str, default='D:\GGR\H\VISH-VEP19')
    options = argpase.parse_args()

    param_excel_fp = os.path.join(options.infolder, options.param_excel_fp)
    modifications = os.path.join(options.visum_folder, 'Modifications')
    shared_data = os.path.join(options.visum_folder, 'SharedData')

    dm = VisemDemandModel(modifications,
                          param_excel_fp,
                          )

    #dm.add_nsegs_userdefined(modification_no=444)
    dm.create_transfer(modification_number=22)
    dm.create_transfer_rsa(modification_number=23)
    #dm.write_modification_iv_matrices(modification_no=12)
    #dm.write_modification_ov_matrices(modification_no=14)
