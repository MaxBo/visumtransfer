# -*- coding: utf-8 -*-

from visumtransfer.visum_table import (VisumTable)


class Gebiete(VisumTable):
    name = 'Gebiete'
    code = 'GEBIET'
    _cols = 'NR;XKOORD;YKOORD'
    _pkey = 'NR'


class Anbindung(VisumTable):
    name = 'Anbindungen'
    code = 'ANBINDUNG'
    _cols = 'BEZNR;KNOTNR;RICHTUNG;VSYSSET'
    _pkey = 'BEZNR;KNOTNR;RICHTUNG;VSYSSET'


class Haltestelle(VisumTable):
    name = 'Haltestellen'
    code = 'HALTESTELLE'
    _cols = 'NR;XKOORD;YKOORD'
    _pkey = 'NR'


class Haltestellenbereich(VisumTable):
    name = 'Haltestellenbereiche'
    code = 'HALTESTELLENBEREICH'
    _cols = 'NR;HSTNR;XKOORD;YKOORD'
    _pkey = 'NR'


class Haltepunkt(VisumTable):
    name = 'Haltepunkte'
    code = 'HALTEPUNKT'
    _cols = 'NR;HSTBERNR;CODE;NAME;TYPNR;VSYSSET;DEPOTFZGKOMBMENGE;GERICHTET;KNOTNR;VONKNOTNR;STRNR;RELPOS;ZWERT1'
    _pkey = 'NR'


class HaltestellenbereichsUebergangsgehzeiten(VisumTable):
    name = 'Haltestellenbereichs-Übergangsgehzeiten'
    code = 'UEBERGANGSGEHZEITHSTBER'
    _cols = 'VONHSTBERNR;NACHHSTBERNR;VSYSCODE;ZEIT'
    _pkey = 'VONHSTBERNR;NACHHSTBERNR;VSYSCODE'


class HaltestellenZuTarifzonen(VisumTable):
    name = 'Haltestellen zu Tarifzonen'
    code = 'HSTZUTARIFZONE'
    _cols = 'TARIFZONENNR;HSTNR'
    _pkey = 'TARIFZONENNR;HSTNR'


class Punkt(VisumTable):
    name = 'Punkte'
    code = 'PUNKT'
    _cols = 'ID;XKOORD;YKOORD'
    _pkey = 'ID'


class Zwischenpunkt(VisumTable):
    name = 'Zwischenpunkte'
    code = 'ZWISCHENPUNKT'
    _cols = 'KANTEID;INDEX;XKOORD;YKOORD'
    _pkey = 'KANTEID;INDEX'


class POI1(VisumTable):
    name = 'Points of Interest'
    code = 'POIOFCAT_1'
    _cols = 'KATNR;NR;XKOORD;YKOORD'
    _pkey = 'KATNR;NR'


class Screenlinepolygon(VisumTable):
    name = 'Screenlinepolygone'
    code = 'SCREENLINEPOLY'
    _cols = 'SCREENLINENR;INDEX;XKOORD;YKOORD'
    _pkey = 'SCREENLINENR;INDEX'


class Knoten(VisumTable):
    name = 'Knoten'
    code = 'KNOTEN'
    _cols = 'NR;XKOORD;YKOORD'
    _pkey = 'NR'


class Strecke(VisumTable):
    name = 'Strecken'
    code = 'STRECKE'
    _cols = 'NR;VONKNOTNR;NACHKNOTNR;LAENGE;VONKNOTENORIENTIERUNG;NACHKNOTENORIENTIERUNG'
    _pkey = 'NR;VONKNOTNR;NACHKNOTNR'


class Streckenpolygone(VisumTable):
    name = 'Streckenpolygone'
    code = 'STRECKENPOLY'
    _cols = 'VONKNOTNR;NACHKNOTNR;INDEX;XKOORD;YKOORD;ZKOORD'
    _pkey = 'VONKNOTNR;NACHKNOTNR;INDEX'


class Abbieger(VisumTable):
    name = 'Abbieger'
    code = 'ABBIEGER'
    _cols = 'VONKNOTNR;UEBERKNOTNR;NACHKNOTNR;TYPNR;VSYSSET;KAPIV;T0IV;Z_ABB_GES;Z_ABB_L;Z_ZAEHLDATUM'
    _pkey = 'VONKNOTNR;UEBERKNOTNR;NACHKNOTNR'


class Oberlinie(VisumTable):
    name = 'Oberlinien'
    code = 'OBERLINIE'
    _cols = 'NAME;KOMMENTAR'
    _pkey = 'NAME'


class Linie(VisumTable):
    name = 'Linien'
    code = 'LINIE'
    _cols = 'NAME;VSYSCODE;FZGKOMBNR;TARIFSYSTEMMENGE;BETREIBERNR;ZWERT1'
    _pkey = 'NAME'


class Systemroute(VisumTable):
    name = 'Systemrouten'
    code = 'SYSTEMROUTE'
    _cols = 'NAME;VSYSCODE;DURCHFAHRZEIT;ANFAHRZUSCHLAG;ABBREMSZUSCHLAG;LAENGE'
    _pkey = 'NAME'
    _converters = {'LAENGE': 'km', }


class SystemroutenVerlaeufe(VisumTable):
    name = 'Systemrouten-Verläufe'
    code = 'SYSTEMROUTENELEMENT'
    _cols = 'SYSROUTENAME;INDEX;KNOTNR;HPUNKTNR'
    _pkey = 'SYSROUTENAME;INDEX'


class Linienroute(VisumTable):
    name = 'Linienrouten'
    code = 'LINIENROUTE'
    _cols = 'LINNAME;NAME;RICHTUNGCODE;ISTRINGLINIE'
    _pkey = 'LINNAME;NAME;RICHTUNGCODE'


class Linienroutenelement(VisumTable):
    name = 'Linienrouten-Verläufe'
    code = 'LINIENROUTENELEMENT'
    _cols = 'LINNAME;LINROUTENAME;RICHTUNGCODE;INDEX;ISTROUTENPUNKT;KNOTNR;HPUNKTNR;NACHLAENGE'
    _pkey = 'LINNAME;LINROUTENAME;RICHTUNGCODE;INDEX'
    _converters = {'NACHLAENGE': 'km', }


class Fahrzeitprofil(VisumTable):
    name = 'Fahrzeitprofile'
    code = 'FAHRZEITPROFIL'
    _cols = 'LINNAME;LINROUTENAME;RICHTUNGCODE;NAME;FZGKOMBNR;REFELEMINDEX'
    _pkey = 'LINNAME;LINROUTENAME;RICHTUNGCODE;NAME'


class Fahrzeitprofilelement(VisumTable):
    name = 'Fahrzeitprofil-Verläufe'
    code = 'FAHRZEITPROFILELEMENT'
    _cols = 'LINNAME;LINROUTENAME;RICHTUNGCODE;FZPROFILNAME;INDEX;LRELEMINDEX;AUS;EIN;ANKUNFT;ABFAHRT'
    _pkey = 'LINNAME;LINROUTENAME;RICHTUNGCODE;FZPROFILNAME;INDEX'


class Fahrplanfahrt(VisumTable):
    name = 'Fahrplanfahrten'
    code = 'FAHRPLANFAHRT'
    _cols = 'NR;NAME;ABFAHRT;LINNAME;LINROUTENAME;RICHTUNGCODE;FZPROFILNAME;VONFZPELEMINDEX;NACHFZPELEMINDEX;BETREIBERNR;TAKTFAHRTGRPNR'
    _pkey = 'NR'


class Fahrplanfahrtabschnitt(VisumTable):
    name = 'Fahrplanfahrtabschnitte'
    code = 'FAHRPLANFAHRTABSCHNITT'
    _cols = 'FPLFAHRTNR;NR;VONFZPELEMINDEX;NACHFZPELEMINDEX;VTAGNR;FZGKOMBNR;FZGKOMBSET'
    _pkey = 'FPLFAHRTNR;NR'


class Fahrplanfahrtkoppelabschnitt(VisumTable):
    name = 'Fahrplanfahrt-Koppelabschnitte'
    code = 'FPLFAHRTKOPPELABSCHNITT'
    _cols = 'FPLFAHRTNRN;INDEX'
    _pkey = 'FPLFAHRTNR;INDEX'


class Fahrplanfahrtkoppelabschnittselement(VisumTable):
    name = 'Fahrplanfahrt-Koppelabschnittselemente'
    code = 'FPLFAHRTKOPPELABSCHNITTSELEMENT'
    _cols = 'FPLFAHRTNR;VONFPLFAHRTELEMINDEX;NACHFPLFAHRTELEMINDEX;ABSCHNITTFPLFAHRTNRN;ABSCHNITTINDEX'
    _pkey = 'FPLFAHRTNR;VONFPLFAHRTELEMINDEX;NACHFPLFAHRTELEMINDEX'


class Fahrplanfahrtelement(VisumTable):
    name = 'Fahrplanfahrtelemente'
    code = 'FAHRPLANFAHRTELEMENT'
    _cols = 'INDEX;FAHRPLANFAHRT-NUMMER;ANKUNFT;ABFAHRT'
    _pkey = 'INDEX;FAHRPLANFAHRT-NUMMER'


class Fahrzeugeinheiten(VisumTable):
    name = 'Fahrzeugeinheiten'
    code = 'FZGEINHEIT'
    _cols = 'NR;CODE;NAME;VSYSSET;TRIEBFZG;SITZPL;GESAMTPL;KOSTENSATZSTDSERVICE;KOSTENSATZSTDLEER;KOSTENSATZSTDSTAND;KOSTENSATZSTDDEPOT;KOSTENSATZKMSERVICE;KOSTENSATZKMLEER;KOSTENSATZFZGEINHEIT'
    _pkey = 'NR'


class Fahrzeugkombinationen(VisumTable):
    name = 'Fahrzeugkombinationen'
    code = 'FZGKOMB'
    _cols = 'NR;CODE;FZGKOMBSET;NAME'
    _pkey = 'NR'


class FahrzeugkombinationsElemente(VisumTable):
    name = 'Fahrzeugkombinations-Elemente'
    code = 'FZGEINHEITZUFZGKOMB'
    _cols = 'FZGKOMBNR;FZGEINHEITNR;ANZFZGEINH'
    _pkey = 'FZGKOMBNR;FZGEINHEITNR'
