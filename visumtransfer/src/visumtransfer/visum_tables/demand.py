# -*- coding: utf-8 -*-

import numpy as np
import warnings
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
            # Heimataktivität hat keine Strukturgröße
            if a['home']:
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
            is_home_activity = a['home']
            row.rang = a['rank'] or 1
            row.rsa = a['balance']
            row.istheimataktivitaet = is_home_activity
            row.kopplungziel = is_home_activity
            row.base_code = a['composite_activity']
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
            ap_tuple = ap_code.split('_')
            origin_code = ap_tuple[0] + suffix
            dest_code = ap_tuple[1] + suffix
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

    def create_tables(self, params: Params,
                      model: str,
                      suffix=''):
        rows = []
        activity_chains = np.unique(params.trip_chain_rates['code'])
        for ac_code in activity_chains:
            ac_tuple = ac_code.split('_')
            act_seq = ['{c}{s}'.format(c=a, s=suffix) for a in ac_tuple]
            code = '_'.join(act_seq)
            act_chain_sequence = ','.join(act_seq)
            row = self.Row(code=code,
                           name=ac_code,
                           nachfragemodellcode=model,
                           aktivcodes=act_chain_sequence)
            rows.append(row)
        self.add_rows(rows)


class Nachfrageschicht(VisumTable):
    name = 'Nachfrageschichten'
    code = 'NACHFRAGESCHICHT'
    _cols = 'CODE;NAME;NACHFRAGEMODELLCODE;AKTKETTENCODE;PGRUPPENCODES;NSEGSET'

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
                row.code = row.name
            else:
                row.code = '_'.join([pgr_code, ac_code])
            row.aktkettencode = ac_code
            row.pgruppencodes = pgr_code
            rows.append(row)
        self.add_rows(rows)

    def create_tables_gd(self,
                         params: Params,
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
