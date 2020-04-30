# coding: utf-8
# (c) Roman Miroshnychenko <roman1972@gmail.com> 2020
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""Classes and function to interact with Kodi API"""

from __future__ import absolute_import, unicode_literals

import os
from inspect import currentframe

from kodi_six import xbmc
from kodi_six.xbmcaddon import Addon

try:
    from typing import Text  # pylint: disable=unused-import
except ImportError:
    pass


ADDON = Addon()
ADDON_ID = ADDON.getAddonInfo('id')
VERSION = ADDON.getAddonInfo('version')
PROFILE_DIR = xbmc.translatePath(ADDON.getAddonInfo('profile'))


class logger(object):  # pylint: disable=invalid-name
    # pylint: disable=missing-docstring
    FORMAT = '{id} [v.{version}] - {filename}:{lineno} - {message}'

    @classmethod
    def _write_message(cls, message, level=xbmc.LOGDEBUG):
        # type: (Text, int) -> None
        curr_frame = currentframe()
        xbmc.log(
            cls.FORMAT.format(
                id=ADDON_ID,
                version=VERSION,
                filename=os.path.basename(curr_frame.f_back.f_back.f_code.co_filename),
                lineno=curr_frame.f_back.f_back.f_lineno,
                message=message
            ),
            level
        )

    @classmethod
    def info(cls, message):
        # type: (Text) -> None
        cls._write_message(message, xbmc.LOGINFO)

    @classmethod
    def warning(cls, message):
        # type: (Text) -> None
        cls._write_message(message, xbmc.LOGWARNING)

    @classmethod
    def error(cls, message):
        # type: (Text) -> None
        cls._write_message(message, xbmc.LOGERROR)

    @classmethod
    def debug(cls, message):
        # type: (Text) -> None
        cls._write_message(message, xbmc.LOGDEBUG)
