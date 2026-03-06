# -*- coding: utf-8 -*-

from visumtransfer.visum_table import VisumTable


class Territory(VisumTable):
    name = 'Territories'
    code = 'TERRITORY'
    _cols = 'NO;XCOORD;YCOORD'
    _pkey = 'NO'


class Connector(VisumTable):
    name = 'Connectors'
    code = 'CONNECTOR'
    _cols = 'ZONENO;NODENO;DIRECTION;TSYSSET'
    _pkey = 'ZONENO;NODENO;DIRECTION;TSYSSET'


class Point(VisumTable):
    name = 'Points'
    code = 'POINT'
    _cols = 'ID;XCOORD;YCOORD'
    _pkey = 'ID'


class EdgeItem(VisumTable):
    name = 'EdgeItems'
    code = 'EDGEITEM'
    _cols = 'EDGEID;INDEX;XCOORD;YCOORD'
    _pkey = 'EDGEID;INDEX'


class ScreenlinePoly(VisumTable):
    name = 'ScreenlinePolygons'
    code = 'SCREENLINEPOLY'
    _cols = 'SCREENLINENO;INDEX;XCOORD;YCOORD'
    _pkey = 'SCREENLINENO;INDEX'


class Node(VisumTable):
    name = 'Nodes'
    code = 'NODE'
    _cols = 'NO;XCOORD;YCOORD'
    _pkey = 'NO'


class Link(VisumTable):
    name = 'Links'
    code = 'LINK'
    _cols = 'NO;FROMNODENO;TONODENO;LENGTH;FROMNODEORIENTATION;TONODEORIENTATION'
    _pkey = 'NO;FROMNODENO;TONODENO'


class LinkPoly(VisumTable):
    name = 'LinkPolygons'
    code = 'LINKPOLY'
    _cols = 'FROMNODENO;TONODENO;INDEX;XCOORD;YCOORD;ZCOORD'
    _pkey = 'FROMNODENO;TONODENO;INDEX'


class Turn(VisumTable):
    name = 'Turns'
    code = 'TURN'
    _cols = 'FROMNODENO;VIANODENO;TONODENO;TYPENO;TSYSSET;CAPPRT;T0PRT'
    _pkey = 'FROMNODENO;VIANODENO;TONODENO'
