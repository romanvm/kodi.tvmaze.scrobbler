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

"""Service entry point"""

from __future__ import absolute_import, unicode_literals

import xbmc

from libs.exception_logger import log_exception
from libs.kodi_monitor import KodiMonitor
from libs.kodi_service import logger
from libs.scheduled_tasks import periodic_pull

with log_exception():
    xbmc.sleep(3000)
    monitor = KodiMonitor()
    logger.info('Service started')
    while not monitor.abortRequested():
        periodic_pull()
        xbmc.sleep(10000)
    logger.info('Service stopped')
