import os
import pytest
import numpy as np
import pandas as pd
from visumtransfer.visum_table import (VisumTable,
                                       VisumTables,
                                       VisumTransfer,
                                       Version)
from visumtransfer.visum_attributes import VisumAttributes
from visumtransfer.visum_tables import (create_userdefined_table,
                                        Tabellendefinition,
                                        BenutzerdefiniertesAttribut,
                                        Netz)


@pytest.fixture
def dataframe() -> pd.DataFrame:
    df = pd.DataFrame(data=np.array([(2, 'A', 33.3),
                                     (4, 'B', 44.4)]),
                      columns=['ID', 'NAME', 'Value'])
    return df


@pytest.fixture
def df_zones() -> pd.DataFrame:
    df = pd.DataFrame(data=np.array([(2, 'A-Stadt', 3),
                                     (4, 'B-Dorf', 4)]),
                      columns=['NO', 'NAME', 'TYPNR'])
    return df


@pytest.fixture(scope='function')
def visum_tables():
    tables = VisumTables()
    return tables


@pytest.fixture
def visum_attribute_file() -> str:
    return os.path.join(os.path.dirname(os.path.dirname(__file__)),
                        'attributes.h5')


@pytest.fixture
def visum_attribute_excelfile() -> str:
    return os.path.join(os.path.dirname(os.path.dirname(__file__)),
                        'attribute.xlsx')


class DummyTable(VisumTable):
    name = 'Dummies'
    code = 'DUMMY'
    _cols = 'ID;NAME;VALUE'
    _pkey = 'ID'
    _defaults = {'VALUE': -11, }


class Bezirke(VisumTable):
    name = 'Bezirke'
    code = 'BEZIRK'
    _cols = 'NR'


class TestVisumTableCreation:
    def test_findVisumTable(self, visum_tables):
        """Test if the VisumTable ist found"""
        # test if table defined in other module is recognized
        assert 'VERSION' in visum_tables.tables
        assert visum_tables.tables['VERSION'] == Version
        # test if table defined in this module is recognized
        assert 'DUMMY' in visum_tables.tables
        assert visum_tables.tables['DUMMY'] == DummyTable


class TestVisumAttributes:
    """test the visum attributes"""
    @pytest.mark.skip(msg="attributes are normally already converted")
    def test_convert_attributes(self,
                                visum_attribute_file,
                                visum_attribute_excelfile):
        visum_attributes = VisumAttributes.from_excel(
            h5file=visum_attribute_file,
            excel_file=visum_attribute_excelfile)

    def test_get_attribute(self, visum_attribute_file):
        visum_attributes = VisumAttributes.from_hdf(visum_attribute_file)
        tables = visum_attributes.tables.reset_index().set_index('Plural(DEU)')
        row = tables.loc['Bezirke']
        assert row.Name == 'Zone'


class TestVisumTransfer:
    """"""
    def test_add_rows(self, dataframe):
        """test adding rows to the DataFrame"""
        tbl = DummyTable(mode='+')
        new_row = tbl.Row(id=2)
        assert new_row.value == DummyTable._defaults['VALUE']
        assert new_row.id == 2
        new_row.name = 'ABC'
        assert new_row.name == 'ABC'

        tbl.add_row(new_row)
        assert len(tbl) == 1
        self.assert_row_equals(tbl, new_row)

        new_row = tbl.Row(id=3, name='DDD')

        tbl.add_row(new_row)
        assert len(tbl) == 2
        self.assert_row_equals(tbl, new_row)

        #  duplicate primary key should raise a ValueError
        new_row = tbl.Row(id=2, name='EEE')
        with pytest.raises(ValueError,
                           match=r'Indexes have overlapping values'):
            tbl.add_row(new_row)
        assert len(tbl) == 2

        #  test adding five more rows with ids 10-14
        new_rows = [tbl.Row(id=n) for n in range(10, 15)]
        tbl.add_rows(new_rows)
        assert len(tbl) == 7
        # the penultimate should have the no 13
        self.assert_row_equals(tbl, tbl.Row(id=13), -2, )

    def assert_row_equals(self,
                          table: VisumTable,
                          row: 'VisumTable.Row',
                          rowno: int = - 1, ):
        """
        compare the nth row in the dataframe to the row

        Parameters
        ----------
        rowno : int, optional (Default=-1)
            then row number in the dataframe
        row : VisumTable.Row
            a recordclass to compare the values
        """
        df_row = table.df.reset_index().iloc[rowno].tolist()
        assert df_row == list(row)

    def test_userdef_table(self, visum_tables):
        """Test a userdefined table"""
        tabledef = Tabellendefinition(mode='+')
        userdef = BenutzerdefiniertesAttribut(mode='+')

        TBL = create_userdefined_table('AAA',
                                       cols_types={'Col1': 'Double',
                                                   'Col2': 'Int',
                                                   'Col3': 'LongText',
                                                   'Col12': 'Double', },
                                       defaults={'COL2': 42, },
                                       col_attrs={'Col1': {'minwert': 0,
                                                           'maxwert': 1, },
                                                  'Col12': {'formel': '[Col1]*[Col2]',
                                                            }, },
                                       tabledef=tabledef,
                                       userdef=userdef)

        tbl = TBL(mode='')
        tbl.add_row(tbl.Row(col1=0.33, col3='Hallo'))
        tbl.add_row(tbl.Row(col1=0.2, col2=4, col3='Hallo'))
        tbl.add_row(tbl.Row(nr=4, col1=0.2, col2=4, col3='Hallo'))
        tbl.add_row(tbl.Row(col1=0.2, col2=4, col3='Hallo'))

        print(tabledef.df)
        print(userdef.df)
        print(tbl.df)

        vt = VisumTransfer.new_transfer()
        vt.tables['TabDefs'] = tabledef
        vt.tables['BenutzerdefinierteAttribute'] = userdef
        vt.tables['tbl1'] = tbl
        vt.write(r'E:\tmp\a.tra')

    def test_netz(self):
        netz = Netz(new_cols=['A', 'B'])
        netz.add_row(netz.Row(a=4, b=7))
        print(netz.df)
        with pytest.raises(ValueError):
            netz.add_row(netz.Row(a=7, b=9))
        assert netz.df.loc[0, 'A'] == 4
        assert netz.df.loc[0, 'B'] == 7
