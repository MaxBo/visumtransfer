from typing import Dict
from visumtransfer.visum_table import VisumTable, MetaClass
from .base import UserDefinedAttribute


class TableDefinition(VisumTable):
    name = 'TableDefinitions'
    code = 'TABLEDEFINITION'
    _cols = 'NAME;GROUP;COMMENT'
    _pk = 'name'


def create_userdefined_table(name: str,
                             cols_types: Dict[str, str],
                             defaults: dict = {},
                             col_attrs: Dict[str, str] = {},
                             group: str = '',
                             comment: str = '',
                             tabledef: TableDefinition = None,
                             userdef: UserDefinedAttribute = None) -> VisumTable:
    """create a userdefined table"""
    colnames = ['TABLEDEFINITIONNAME', 'NO'] + [col for col in cols_types.keys()
                                               if not 'formula' in col_attrs.get(col, {})]
    tbl_name = f'Tabelleneinträge: {name}'
    tbl_code = f'TABLEENTRIES_{name}'
    defaults['TABLEDEFINITIONNAME'] = name
    defaults['NO'] = None

    cls = MetaClass(tbl_code, (VisumTable, ), {'name': tbl_name,
                                             'code': tbl_code,
                                             '_cols': ';'.join(colnames),
                                             '_defaults': defaults,
                                             '_pkey': 'NO',
                                               })

    tabledef = TableDefinition(mode='+') if tabledef is None else tabledef
    tabledef.add(name=name, group=group, comment=comment)

    userdef = UserDefinedAttribute(mode='+') if userdef is None else userdef
    for col, dtype in cols_types.items():
        attrs = col_attrs.get(col, {})
        if 'formula' in attrs:
            datasourcetype = attrs.pop('datasourcetype', None)
            userdef.add_formula_attribute(objid=tbl_code,
                                          name=col,
                                          valuetype=dtype,
                                          **attrs,
                                           )
        else:
            userdef.add_data_attribute(objid=tbl_code,
                                        name=col,
                                        valuetype=dtype,
                                        **attrs,
                                        )
    return cls
