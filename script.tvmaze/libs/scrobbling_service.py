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

"""Scrobbling-related functionality"""

# pylint: disable=missing-docstring

from __future__ import absolute_import, division, unicode_literals

import time

try:
    from typing import Text, Dict, Any, List, Tuple  # pylint: disable=unused-import
except ImportError:
    pass

SUPPORTED_IDS = ('tvmaze', 'tvdb', 'imdb')


class StatusType(object):  # pylint: disable=too-few-public-methods
    WATCHED = 0
    ACQUIRED = 1
    SKIPPED = 2


def get_unique_id(unique_ids):
    # type: (Dict[Text, Text]) -> Tuple[Text, Text]
    """
    Get a show ID in one of the supported online databases

    :param unique_ids: uniqueid dict from Kodi JSON-RPC API
    :return: a tuple of unique ID and online data provider
    :raises LookupError: if a unique ID cannot be determined
    """
    for provider in SUPPORTED_IDS:
        unique_id = unique_ids.get(provider)
        if unique_id is not None:
            if provider == 'tvdb':
                provider = 'thetvdb'
            return unique_id, provider
    raise LookupError


def prepare_episode_list(kodi_episode_list):
    # type: (List[Dict[Text, Any]]) -> List[Dict[Text, int]]
    episodes_for_tvmaze = []
    for episode in kodi_episode_list:
        if episode['season']:  # Todo: add support for specials
            episodes_for_tvmaze.append({
                'season': episode['season'],
                'episode': episode['episode'],
                'marked_at': int(time.time()),
                'type': StatusType.WATCHED if episode['playcount'] else StatusType.ACQUIRED,
            })
    return episodes_for_tvmaze
