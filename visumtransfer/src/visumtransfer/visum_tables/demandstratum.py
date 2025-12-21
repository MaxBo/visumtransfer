# -*- coding: utf-8 -*-

from .persongroups import PersonGroup
from .activities import Activity, Activitychain
from visumtransfer.visum_table import VisumTable


class DemandStratum(VisumTable):
    name = 'DemandStrata'
    code = 'DEMANDSTRATUM'
    _cols = 'CODE;NAME;DEMANDMODELCODE;ACTIVITYCHAINCODE;PERSONGROUPCODES;DSEGSET;MOBILITAETSRATE;TARIFMATRIX;MAINACTCODE'

    def create_tables_gd(self,
                         personengruppe: PersonGroup,
                         activity: Activity,
                         activitychain: Activitychain,
                         dsegset: str = 'O,F,M,P,R',
                         model: str = 'VisemGGR',
                         category: str = 'ZielVMWahl'):
        ac_hierarchy = activity.get_hierarchy()
        rows = []
        pgroups = personengruppe.df
        pgroups.fillna({'TARIFMATRIX': ''}, inplace=True)
        pg_gd = pgroups.loc[pgroups['CATEGORY'] == category]
        for pgr_code, gd in pg_gd.iterrows():
            for ac_code, mobilityrate in personengruppe.gd_codes[pgr_code]:
                dstratcode = ':'.join((pgr_code, ac_code))
                # get the main activity of the person group
                sequence = activitychain.df.loc[ac_code, 'ACTIVITYCODES']
                main_act_code = activity.get_main_activity(ac_hierarchy, sequence)
                # take the tarifmatrix defined for the main activity
                tarifmatrix = activity.df.loc[main_act_code, 'TARIFMATRIX']
                for group_code in gd['GROUPS_CONSTANTS'].split(','):
                    # if there is a special tarifmatrix defined for a persongroup,
                    # take this one instead of the activity-Tarifmatrix
                    tarifmatrix = personengruppe.df.loc[group_code,
                                                        'TARIFMATRIX'] or tarifmatrix


                row = self.Row(code=dstratcode,
                               name=dstratcode,
                               demandmodelcode=model,
                               persongroupcodes=pgr_code,
                               activitychaincode=ac_code,
                               mainactcode=main_act_code,
                               dsegset=dsegset,
                               mobilitaetsrate=mobilityrate,
                               tarifmatrix=tarifmatrix,
                               )
                rows.append(row)
        self.add_rows(rows)
