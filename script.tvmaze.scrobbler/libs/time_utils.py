# coding: utf-8
from __future__ import absolute_import, unicode_literals

import datetime

import pytz

from .kodi_service import logger
from .medialibrary_api import get_kodi_timezone_string

try:
    from typing import Text, Optional  # pylint: disable=unused-import
except ImportError:
    pass


def get_kodi_timezone():
    # type: () -> Optional[pytz.tzinfo.DstTzInfo]
    kodi_timezone_string = get_kodi_timezone_string()
    try:
        return pytz.timezone(kodi_timezone_string)
    except pytz.UnknownTimeZoneError:
        logger.error('Unable to determine Kodi timezone from string: "{}"'.format(
            kodi_timezone_string))
    return None


def convert_to_time_string(posix_timestamp):
    # type: (int) -> Text
    kodi_timezone = get_kodi_timezone()
    date_time = datetime.datetime.fromtimestamp(posix_timestamp, tz=kodi_timezone)
    return date_time.strftime('%Y-%m-%d %H:%M:%S')
