# -*- coding: utf-8 -*-

from .persongroups import Personengruppe
from visumtransfer.visum_table import VisumTable


class Nachfrageschicht(VisumTable):
    name = 'Nachfrageschichten'
    code = 'NACHFRAGESCHICHT'
    _cols = 'CODE;NAME;NACHFRAGEMODELLCODE;AKTKETTENCODE;PGRUPPENCODES;NSEGSET;MOBILITAETSRATE'

    def create_tables_gd(self,
                         personengruppe: Personengruppe,
                         nsegset: str = 'A,F,M,P,R',
                         model: str = 'VisemGGR',
                         category: str = 'ZielVMWahl'):
        rows = []
        pgroups = personengruppe.df
        pg_gd = pgroups.loc[pgroups['CATEGORY'] == category]
        for pgr_code, gd in pg_gd.iterrows():
            for ac_code, mobilitaetsrate in personengruppe.gd_codes[pgr_code]:
                dstratcode = ':'.join((pgr_code, ac_code))
                row = self.Row(code=dstratcode,
                               name=dstratcode,
                               nachfragemodellcode=model,
                               pgruppencodes=pgr_code,
                               aktkettencode=ac_code,
                               nsegset=nsegset,
                               mobilitaetsrate=mobilitaetsrate,
                               )
                rows.append(row)
        self.add_rows(rows)
