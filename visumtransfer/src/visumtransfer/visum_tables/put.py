# -*- coding: utf-8 -*-

from visumtransfer.visum_table import VisumTable


class Stop(VisumTable):
    name = 'Stops'
    code = 'STOP'
    _cols = 'NO;XCOORD;YCOORD'
    _pkey = 'NO'


class StopArea(VisumTable):
    name = 'StopAreas'
    code = 'STOPAREA'
    _cols = 'NO;STOPNO;XCOORD;YCOORD'
    _pkey = 'NO'


class StopPoint(VisumTable):
    name = 'StopPoints'
    code = 'STOPPOINT'
    _cols = 'NO;STOPAREANO;CODE;NAME;TYPENO;TSYSSET;DEPOTVEHCOMBSET;DIRECTED;NODENO;FROMNODENO;LINKNO;RELPOS;ADDVAL1'
    _pkey = 'NO'


class TransferWalkTimeStopArea(VisumTable):
    name = 'Transfer WalkTime between StopAreas'
    code = 'TRANSFERWALKTIMESTOPAREA'
    _cols = 'FROMSTOPAREANO;TOSTOPAREANO;TSYSCODE;TIME'
    _pkey = 'FROMSTOPAREANO;TOSTOPAREANO;TSYSCODE'


class StopToFareZone(VisumTable):
    name = 'Stop To FareZone'
    code = 'STOPTOFAREZONE'
    _cols = 'FAREZONENO;STOPNO'
    _pkey = 'FAREZONENO;STOPNO'


class MainLine(VisumTable):
    name = 'MainLines'
    code = 'MAINLINE'
    _cols = 'NAME;COMMENT'
    _pkey = 'NAME'


class Line(VisumTable):
    name = 'Lines'
    code = 'LINE'
    _cols = 'NAME;TSYSCODE;VEHCOMBNO;FARESYSTEMSET;OPERATORNO;ADDVAL1'
    _pkey = 'NAME'


class SysRoute(VisumTable):
    name = 'System Routes'
    code = 'SYSROUTE'
    _cols = 'NAME;TSYSCODE;TNONSTOP;TSTARTSTOP;TENDSTOP;LENGTH'
    _pkey = 'NAME'
    _converters = {'LENGTH': 'km', }


class SysRouteItem(VisumTable):
    name = 'SystemRoute Items'
    code = 'SYSROUTEITEM'
    _cols = 'SYSROUTENAME;INDEX;NODENO;STOPPOINTNO'
    _pkey = 'SYSROUTENAME;INDEX'


class LineRoute(VisumTable):
    name = 'LineRoutes'
    code = 'LINEROUTE'
    _cols = 'LINENAME;NAME;DIRECTIONCODE;ISCIRCLELINE'
    _pkey = 'LINENAME;NAME;DIRECTIONCODE'


class LineRouteItem(VisumTable):
    name = 'LineRoute Items'
    code = 'LINEROUTEITEM'
    _cols = 'LINENAME;LINEROUTENAME;DIRECTIONCODE;INDEX;ISROUTEPOINT;NODENO;STOPPOINTNO;POSTLENGTH'
    _pkey = 'LINENAME;LINEROUTENAME;DIRECTIONCODE;INDEX'
    _converters = {'POSTLENGTH': 'km', }


class TimeProfile(VisumTable):
    name = 'TimeProfiles'
    code = 'TIMEPROFILE'
    _cols = 'LINENAME;LINEROUTENAME;DIRECTIONCODE;NAME;VEHCOMBNO;REFITEMINDEX'
    _pkey = 'LINENAME;LINEROUTENAME;DIRECTIONCODE;NAME'


class TimeProfileItem(VisumTable):
    name = 'TimeProfile Items'
    code = 'TIMEPROFILEITEM'
    _cols = 'LINENAME;LINEROUTENAME;DIRECTIONCODE;TIMEPROFILENAME;INDEX;LRITEMINDEX;ALIGHT;BOARD;ARR;DEP'
    _pkey = 'LINENAME;LINEROUTENAME;DIRECTIONCODE;TIMEPROFILENAME;INDEX'


class VehJourney(VisumTable):
    name = 'VehJourneys'
    code = 'VEHJOURNEY'
    _cols = 'NO;NAME;DEP;LINENAME;LINEROUTENAME;DIRECTIONCODE;TIMEPROFILENAME;FROMTPROFITEMINDEX;TOTPROFITEMINDEX;OPERATORNO;SERVTRIPPATNO'
    _pkey = 'NO'


class VehJourneySection(VisumTable):
    name = 'VehJourneySections'
    code = 'VEHJOURNEYSECTION'
    _cols = 'VEHJOURNEYNO;NO;FROMTPROFITEMINDEX;TOTPROFITEMINDEX;VALIDDAYSNO;VEHCOMBNO;FZGKOMBSET'
    _pkey = 'VEHJOURNEYNO;NO'


class VehJourneyCoupleSection(VisumTable):
    name = 'VehJourneyCoupleSections'
    code = 'VEHJOURNEYCOUPLESECTION'
    _cols = 'VEHJOURNEYNOS;INDEX'
    _pkey = 'VEHJOURNEYNOS;INDEX'


class VehJourneyCoupleSectionItem(VisumTable):
    name = 'VehJourneyCoupleSectionItems'
    code = 'VEHJOURNEYCOUPLESECTIONITEM'
    _cols = 'VEHJOURNEYNO;FROMVEHJOURNEYITEMINDEX;TOVEHJOURNEYITEMINDEX;SECTVEHJOURNEYNOS;SECTINDEX'
    _pkey = 'VEHJOURNEYNO;FROMVEHJOURNEYITEMINDEX;TOVEHJOURNEYITEMINDEX'


class VehJourneyItem(VisumTable):
    name = 'VehJourneyItems'
    code = 'VEHJOURNEYITEM'
    _cols = 'INDEX;VEHJOURNEYNO;ARR;DEP'
    _pkey = 'INDEX;VEHJOURNEYNO'


class VehUnit(VisumTable):
    name = 'VehicleUnits'
    code = 'VEHUNIT'
    _cols = 'NO;CODE;NAME;TSYSSET;POWERED;SEATCAP;TOTALCAP;COSTRATEHOURSERVICE;COSTRATEHOUREMPTY;COSTRATEHOURLAYOVER;COSTRATEHOURDEPOT;COSTRATEKMSERVICE;COSTRATEKMEMPTY;COSTRATEVEHUNIT'
    _pkey = 'NO'


class VehComb(VisumTable):
    name = 'VehicleCombinations'
    code = 'VEHCOMB'
    _cols = 'NO;CODE;VEHCOMBSET;NAME'
    _pkey = 'NO'


class VehUnitToVehComb(VisumTable):
    name = 'Vehicle Units in Vehicle Combinations'
    code = 'VEHUNITTOVEHCOMB'
    _cols = 'VEHCOMBNO;VEHUNITNO;NUMVEHUNITS'
    _pkey = 'VEHCOMBNO;VEHUNITNO'


class TicketTypeToDSegFareSystem(VisumTable):
    name = 'TicketType-DSeg-FareSystems'
    code = 'TICKETTYPETODSEGFARESYSTEM'
    _cols = 'FARESYSTEMNO;DSEGCODE;TICKETTYPENO'
