from typing import Dict
from visumtransfer.visum_table import VisumTable, MetaClass
from visumtransfer.visum_tables.basis import BenutzerdefiniertesAttribut


class Tabellendefinition(VisumTable):
    name = 'Tabellendefinitionen'
    code = 'TABELLENDEFINITION'
    _cols = 'NAME;GRUPPE;KOMMENTAR'
    _pk = 'name'


def create_userdefined_table(name: str,
                             cols_types: Dict[str, str],
                             defaults: dict = {},
                             col_attrs: Dict[str, str] = {},
                             group: str = '',
                             kommentar: str = '',
                             tabledef: Tabellendefinition = None,
                             userdef: BenutzerdefiniertesAttribut = None) -> VisumTable:
    """create a userdefined table"""
    colnames = ['TABELLENDEFINITIONNAME', 'NR'] + [col for col in cols_types.keys()
                                               if not 'formel' in col_attrs.get(col, {})]
    tbl_name = f'Tabelleneinträge: {name}'
    tbl_code = f'TABLEENTRIES_{name}'
    defaults['TABELLENDEFINITIONNAME'] = name

    cls = MetaClass(tbl_code, (VisumTable, ), {'name': tbl_name,
                                             'code': tbl_code,
                                             '_cols': ';'.join(colnames),
                                             '_defaults': defaults, })

    tabledef = Tabellendefinition(mode='+') if tabledef is None else tabledef
    tabledef.add_row(tabledef.Row(name=name, gruppe=group))

    userdef = BenutzerdefiniertesAttribut(mode='+') if userdef is None else userdef
    for col, dtype in cols_types.items():
        attrs = col_attrs.get(col, {})
        if 'formel' in attrs:
            datenquellentyp = attrs.pop('datenquellentyp', None)
            userdef.add_formel_attribute(objid=tbl_code,
                                        name=col,
                                        datentyp=dtype,
                                        **attrs,
                                         )
        else:
            userdef.add_daten_attribute(objid=tbl_code,
                                        name=col,
                                        datentyp=dtype,
                                        **attrs,
                                        )
    return cls
