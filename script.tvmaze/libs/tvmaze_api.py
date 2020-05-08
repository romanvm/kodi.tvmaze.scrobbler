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

from .kodi_service import logger

try:
    from typing import Union, Text, List, Optional, Tuple  # pylint: disable=unused-import
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


class AuthorizationError(Exception):  # pylint: disable=missing-docstring
    pass


def call_api(url, method='get', **requests_kwargs):
    # type: (Text, Text, **Optional[Union[tuple, dict]]) -> Union[dict, List[dict]]
    """Call TVmaze API"""
    method_func = getattr(SESSION, method, SESSION.get)
    auth = requests_kwargs.pop('auth', None)  # Remove credentials before logging
    logger.debug(
        'Calling URL "{}"... method: {}, parameters: {}'.format(
            url, method, pformat(requests_kwargs))
    )
    response = method_func(url, auth=auth, **requests_kwargs)
    if not response.ok:
        logger.error('TVmaze returned error {}: {}'.format(response.status_code, response.text))
        response.raise_for_status()
    response_json = response.json()
    return response_json


def start_authorization(email):
    # type: (Text) -> Tuple[Text, Text]
    """
    Start scraper authorization flow

    :return: (authorization token, confirmation url) tuple
    """
    url = API_URL + AUTH_START_PATH
    data = {
        'email': email,
        'email_confirmation': True,
    }
    try:
        response_data = call_api(url, 'post', json=data)
    except requests.exceptions.HTTPError as exc:
        raise_from(AuthorizationError(exc.response.text), exc)
    return response_data.get('token'), response_data.get('confirm_url')


def poll_authorization(token):
    # type: (Text) -> Optional[Tuple[Text, Text]]
    """
    Poll authorization confirmation

    :return: (TVmaze username, API key) tuple
    """
    url = API_URL + AUTH_POLL_PATH
    try:
        response_data = call_api(url, 'post', json={'token': token})
    except requests.exceptions.HTTPError as exc:
        if exc.response.status_code == 403:
            return None
        raise_from(AuthorizationError(exc.response.text), exc)
    return response_data.get('username'), response_data.get('apikey')
