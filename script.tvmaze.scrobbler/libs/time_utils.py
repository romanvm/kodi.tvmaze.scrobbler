# coding: utf-8
from __future__ import absolute_import, unicode_literals

import datetime
import time

import pytz

from .kodi_service import logger
from .medialibrary_api import send_json_rpc

try:
    from typing import Text, Optional  # pylint: disable=unused-import
except ImportError:
    pass

DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'
TIMEZONE = None


class proxydt(datetime.datetime):  # pylint: disable=invalid-name
    """
    A hack to fix Kodi datetime.strptime problem

    More info: https://forum.kodi.tv/showthread.php?tid=112916
    """

    @classmethod
    def strptime(cls, date_string, format):  # pylint: disable=redefined-builtin
        return datetime.datetime(*(time.strptime(date_string, format)[0:6]))


datetime.datetime = proxydt


def _get_kodi_timezone():
    # type: () -> Optional[pytz.tzinfo.DstTzInfo]
    global TIMEZONE  # pylint: disable=global-statement
    if TIMEZONE is None:
        method = 'Settings.GetSettingValue'
        params = {'setting': 'locale.timezone'}
        result = send_json_rpc(method, params)
        kodi_timezone = result.get('value')
        try:
            TIMEZONE = pytz.timezone(kodi_timezone)
        except pytz.UnknownTimeZoneError:
            logger.error('Unable to create a pytz timezone from Kodi timezone: "{}"'.format(
                kodi_timezone))
    return TIMEZONE


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
