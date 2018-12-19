# -*- coding: utf-8 -*-


def get_visum_user(Visum):
    """Return the Visum User"""
    license = Visum.LicenseManager.CurrentLicenseInfo
    return license.AttValue('LicenseName')


