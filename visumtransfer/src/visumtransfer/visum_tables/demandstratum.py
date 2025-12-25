# -*- coding: utf-8 -*-

from .activities import Activity, Activitychain
from visumtransfer.visum_table import VisumTable


class DemandStratum(VisumTable):
    name = 'DemandStrata'
    code = 'DEMANDSTRATUM'
    _cols = 'CODE;NAME;DEMANDMODELCODE;ACTIVITYCHAINCODE;PERSONGROUPCODES;DSEGSET;MOBILITYRATE;TARIFMATRIX;MAINACTCODE'
