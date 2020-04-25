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

"""Functions to work with TVmaze API"""

from __future__ import absolute_import, unicode_literals

from pprint import pformat

import requests

from .kodi_utils import logger

SESSION = requests.Session()
SESSION.headers.update({
    'User-Agent': 'Kodi scrobbler for tvmaze.com',
    'Accept': 'application/json',
})


def call_api(url, method='get', **requests_kwargs):
    headers = requests_kwargs.pop('headers', {})
    auth = requests_kwargs.pop('auth', None)
    SESSION.headers.update(headers)
    method_func = getattr(SESSION, method, SESSION.get)
    logger.debug('Calling URL "{}"... method: {}, parameters: {}'.format(url, method, requests_kwargs))
    response = method_func(url, auth=auth, **requests_kwargs)
    if not response.ok:
        logger.error('TVmaze returned error {}: {}'.format(response.status_code, response.text))
        response.raise_for_status()
    response_json = response.json()
    logger.debug('TVmaze API response:\n{}'.format(pformat(response_json)))
