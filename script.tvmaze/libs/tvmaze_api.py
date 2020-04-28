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
from six import raise_from

from .kodi_utils import logger

try:
    from typing import Union, Text, List, Optional, Tuple
except ImportError:
    pass

API_URL = 'https://api.staging.tvmaze.net/v1'
AUTH_START_PATH = '/auth/start'
AUTH_POLL_PATH = '/auth/poll'

SESSION = requests.Session()
SESSION.headers.update({
    'User-Agent': 'Kodi scrobbler for tvmaze.com',
    'Accept': 'application/json',
})


class AuthorizationError(Exception):
    pass


def call_api(url, method='get', logging=True, **requests_kwargs):
    # type: (Text, Text, bool, **Optional[Union[tuple, dict]]) -> Union[dict, List[dict]]
    method_func = getattr(SESSION, method, SESSION.get)
    if logging:
        logger.debug('Calling URL "{}"... method: {}, parameters: {}'.format(url, method, pformat(requests_kwargs)))
    response = method_func(url, **requests_kwargs)
    if not response.ok:
        logger.error('TVmaze returned error {}: {}'.format(response.status_code, response.text))
        response.raise_for_status()
    response_json = response.json()
    if logging:
        logger.debug('TVmaze API response:\n{}'.format(pformat(response_json)))
    return response_json


def start_authorization(email):
    # type: (Text) -> Tuple[Text, Text]
    url = API_URL + AUTH_START_PATH
    data = {
        'email': email,
        'email_confirmation': True,
    }
    try:
        response_data = call_api(url, 'post', logging=False, json=data)
    except requests.exceptions.HTTPError as exc:
        message = exc.response.json().get('message', 'unknown')
        raise_from(AuthorizationError(message), exc)
    return response_data.get('token'), response_data.get('confirm_url')


def poll_authorization(token):
    # type: (Text) -> Optional[Tuple[Text, Text]]
    url = API_URL + AUTH_POLL_PATH
    try:
        response_data = call_api(url, 'post', logging=False, json={'token': token})
    except requests.exceptions.HTTPError as exc:
        if exc.response.status_code == 403:
            return None
        message = exc.response.json().get('message', 'unknown')
        raise_from(AuthorizationError(message), exc)
    return response_data.get('username'), response_data.get('apikey')
