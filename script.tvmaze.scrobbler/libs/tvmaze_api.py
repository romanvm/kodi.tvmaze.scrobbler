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
# pylint: disable=missing-docstring

from __future__ import absolute_import, unicode_literals

from pprint import pformat

import requests

from .kodi_service import logger, ADDON

try:
    from typing import Union, Text, List, Optional, Tuple, Dict, Any  # pylint: disable=unused-import
except ImportError:
    pass

API_URL = 'http://api.tvmaze.com'
USER_API_URL = 'https://api.tvmaze.com/v1'
AUTH_START_PATH = '/auth/start'
AUTH_POLL_PATH = '/auth/poll'
SCROBBLE_SHOWS_PATH = '/scrobble/shows'
SHOW_LOOKUP_PATH = '/lookup/shows'

SESSION = requests.Session()
SESSION.headers.update({
    'User-Agent': 'Kodi scrobbler for tvmaze.com',
    'Accept': 'application/json',
})


class AuthorizationError(Exception):
    pass


class UpdateError(Exception):
    pass


class GetInfoError(Exception):
    pass


def _get_credentials():
    # type: () -> Tuple[Text, Text]
    username = ADDON.getSettingString('username')
    apikey = ADDON.getSettingString('apikey')
    return username, apikey


def is_authorized():
    # type: () -> bool
    return all(_get_credentials())


def call_api(url, method='get', **requests_kwargs):
    # type: (Text, Text, **Optional[Union[tuple, dict, list]]) -> requests.Response
    """Call TVmaze API"""
    method_func = getattr(SESSION, method, SESSION.get)
    auth = requests_kwargs.pop('auth', None)  # Remove credentials before logging
    logger.debug(
        'Calling URL "{}"... method: {}, parameters:\n{}'.format(
            url, method, pformat(requests_kwargs))
    )
    response = method_func(url, auth=auth, **requests_kwargs)
    if not response.ok:
        logger.error('TVmaze returned error {}: {}'.format(response.status_code, response.text))
        response.raise_for_status()
    return response


def start_authorization(email):
    # type: (Text) -> Tuple[Text, Text]
    """
    Start scraper authorization flow

    :return: (authorization token, confirmation url) tuple
    """
    url = USER_API_URL + AUTH_START_PATH
    data = {
        'email': email,
        'email_confirmation': True,
    }
    try:
        response = call_api(url, 'post', json=data)
    except requests.exceptions.HTTPError as exc:
        raise AuthorizationError(exc.response.text)
    response_data = response.json()
    return response_data.get('token'), response_data.get('confirm_url')


def poll_authorization(token):
    # type: (Text) -> Optional[Tuple[Text, Text]]
    """
    Poll authorization confirmation

    :return: (TVmaze username, API key) tuple
    """
    url = USER_API_URL + AUTH_POLL_PATH
    try:
        response = call_api(url, 'post', json={'token': token})
    except requests.exceptions.HTTPError as exc:
        if exc.response.status_code == 403:
            return None
        raise AuthorizationError(exc.response.text)
    response_data = response.json()
    return response_data.get('username'), response_data.get('apikey')


def send_episodes(episodes, show_id, provider='tvmaze'):
    # type: (List[Dict[Text, int]], Union[int, Text], Text) -> None
    """
    Send statuses of episodes to TVmase

    :param episodes: the list of episodes to update
    :param show_id: TV show ID in tvmaze, thetvdb or imdb online databases
    :param provider: ID provider
    :raises UpdateError: on update error
    """
    username, apikey = _get_credentials()
    if not (username and apikey):
        raise UpdateError('Missing TVmaze username and API key')
    provider += '_id'
    url = USER_API_URL + SCROBBLE_SHOWS_PATH
    params = {provider: show_id}
    try:
        response = call_api(url, 'post', params=params, json=episodes, auth=(username, apikey))
    except requests.exceptions.HTTPError as exc:
        raise UpdateError(
            'status: {}, message: {}'.format(exc.response.status_code, exc.response.text))
    if response.status_code == 207:
        logger.warning('Failed to update some episode info: {}'.format(response.text))


def get_show_info_by_external_id(show_id, provider):
    # type: (Text, Text) -> Dict[Text, Any]
    """
    Get brief show info from TVmaze by external ID

    :param show_id: show ID in an external online DB
    :param provider: online DB provider
    :return: show info from TVmaze
    :raises GetInfoError: if no show info was found
    """
    url = API_URL + SHOW_LOOKUP_PATH
    params = {provider: show_id}
    try:
        response = call_api(url, 'get', params=params)
    except requests.exceptions.HTTPError:
        raise GetInfoError('Unable to find a show by id {provider}={show_id}')
    return response.json()


def get_episodes_from_watchlist(tvmaze_id, type_=None):
    # type: (Union[int, Text], Optional[int]) -> List[Dict[Text, Any]]
    """
    Get episodes for a TV show from user's watchlist on TVmaze

    :param tvmaze_id: show ID on TVmaze
    :param type_: get only episodes with the given status type
    :return: the list of episode infos from TVmaze
    :raises GetInfoError:
    """
    username, apikey = _get_credentials()
    if not (username and apikey):
        raise UpdateError('Missing TVmaze username and API key')
    path = '{}/{}'.format(SCROBBLE_SHOWS_PATH, tvmaze_id)
    url = USER_API_URL + path
    params = {'embed': 'episode'}
    if type_ is not None:
        params['type'] = type_
    try:
        response = call_api(url, 'get', params=params, auth=(username, apikey))
    except requests.exceptions.HTTPError:
        raise GetInfoError('Unable to get watchlist for show id {}'.format(tvmaze_id))
    return response.json()
