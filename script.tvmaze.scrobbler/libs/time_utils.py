# coding: utf-8
from __future__ import absolute_import, unicode_literals

import datetime
import time

import pytz

from .kodi_service import logger
from .medialibrary_api import get_kodi_timezone_string

try:
    from typing import Text, Optional  # pylint: disable=unused-import
except ImportError:
    pass

DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'


class proxydt(datetime.datetime):
    """
    A hack to fix Kodi datetime.strptime problem

    More info: https://forum.kodi.tv/showthread.php?tid=112916
    """
    def __init__(self, *args, **kwargs):
        super(proxydt, self).__init__(*args, **kwargs)

    @classmethod
    def strptime(cls, date_string, format):
        return datetime.datetime(*(time.strptime(date_string, format)[0:6]))


datetime.datetime = proxydt


def _get_kodi_timezone():
    # type: () -> Optional[pytz.tzinfo.DstTzInfo]
    kodi_timezone_string = get_kodi_timezone_string()
    try:
        return pytz.timezone(kodi_timezone_string)
    except pytz.UnknownTimeZoneError:
        logger.error('Unable to determine Kodi timezone from string: "{}"'.format(
            kodi_timezone_string))
    return None


def timestamp_to_time_string(posix_timestamp):
    # type: (int) -> Text
    kodi_timezone = _get_kodi_timezone()
    date_time = datetime.datetime.fromtimestamp(posix_timestamp, tz=kodi_timezone)
    return date_time.strftime(DATETIME_FORMAT)


def time_string_to_timestamp(time_string):
    # type: (Text) -> int
    time_object = datetime.datetime.strptime(time_string, DATETIME_FORMAT)
    kodi_timezone = _get_kodi_timezone()
    if kodi_timezone is not None:
        time_object = kodi_timezone.localize(time_object)
    timetuple = time_object.timetuple()
    return int(time.mktime(timetuple))
