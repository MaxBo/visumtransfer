# -*- coding: utf-8 -*-

from visumtransfer.visum_table import VisumTable


class Haltestelle(VisumTable):
    name = 'Haltestellen'
    code = 'HALTESTELLE'
    _cols = 'NO;XKOORD;YKOORD'
    _pkey = 'NO'


class Haltestellenbereich(VisumTable):
    name = 'Haltestellenbereiche'
    code = 'HALTESTELLENBEREICH'
    _cols = 'NO;HSTNR;XKOORD;YKOORD'
    _pkey = 'NO'


class Haltepunkt(VisumTable):
    name = 'Haltepunkte'
    code = 'HALTEPUNKT'
    _cols = 'NO;HSTBERNR;CODE;NAME;TYPNR;VSYSSET;DEPOTFZGKOMBMENGE;GERICHTET;KNOTNR;VONKNOTNR;STRNR;RELPOS;ZWERT1'
    _pkey = 'NO'


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


class Oberlinie(VisumTable):
    name = 'Oberlinien'
    code = 'OBERLINIE'
    _cols = 'NAME;COMMENT'
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
    _cols = 'NO;NAME;ABFAHRT;LINNAME;LINROUTENAME;RICHTUNGCODE;FZPROFILNAME;VONFZPELEMINDEX;NACHFZPELEMINDEX;BETREIBERNR;TAKTFAHRTGRPNR'
    _pkey = 'NO'


class Fahrplanfahrtabschnitt(VisumTable):
    name = 'Fahrplanfahrtabschnitte'
    code = 'FAHRPLANFAHRTABSCHNITT'
    _cols = 'FPLFAHRTNR;NO;VONFZPELEMINDEX;NACHFZPELEMINDEX;VTAGNR;FZGKOMBNR;FZGKOMBSET'
    _pkey = 'FPLFAHRTNR;NO'


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
    _cols = 'NO;CODE;NAME;VSYSSET;TRIEBFZG;SITZPL;GESAMTPL;KOSTENSATZSTDSERVICE;KOSTENSATZSTDLEER;KOSTENSATZSTDSTAND;KOSTENSATZSTDDEPOT;KOSTENSATZKMSERVICE;KOSTENSATZKMLEER;KOSTENSATZFZGEINHEIT'
    _pkey = 'NO'


class Fahrzeugkombinationen(VisumTable):
    name = 'Fahrzeugkombinationen'
    code = 'FZGKOMB'
    _cols = 'NO;CODE;FZGKOMBSET;NAME'
    _pkey = 'NO'


class FahrzeugkombinationsElemente(VisumTable):
    name = 'Fahrzeugkombinations-Elemente'
    code = 'FZGEINHEITZUFZGKOMB'
    _cols = 'FZGKOMBNR;FZGEINHEITNR;ANZFZGEINH'
    _pkey = 'FZGKOMBNR;FZGEINHEITNR'


class FahrkartenartZuTarifsystemNSeg(VisumTable):
    name = 'Tarifsystem-NSeg-Fahrkartenarten'
    code = 'FahrkartenartZuTarifsystemNSeg'
    _cols = 'TarifsystemNr;DSEGCODE;FahrkartenartNr'
