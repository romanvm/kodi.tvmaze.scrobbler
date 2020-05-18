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
from pprint import pformat

from .gui import background_progress_dialog
from .kodi_service import logger, LocalizationService
from .medialibrary_api import NoDataError, get_tvshows, get_episodes
from .tvmaze_api import UpdateError, send_episodes

try:
    from typing import Text, Dict, Any, Optional, List, Tuple  # pylint: disable=unused-import
except ImportError:
    pass

_ = LocalizationService().gettext

SUPPORTED_IDS = ('tvmaze', 'tvdb', 'imdb')


def _get_unique_id(unique_ids):
    # type: (Dict[Text, Text]) -> Optional[Tuple[Text, Text]]
    for provider in SUPPORTED_IDS:
        unique_id = unique_ids.get(provider)
        if unique_id is not None:
            if provider == 'tvdb':
                provider = 'thetvdb'
                return unique_id, provider
    return None


def _prepare_episode_list(kodi_episode_list):
    # type: (List[Dict[Text, Any]]) -> List[Dict[Text, int]]
    episodes_for_tvmaze = []
    for episode in kodi_episode_list:
        if episode['season']:  # Todo: add support for specials
            episodes_for_tvmaze.append({
                'season': episode['season'],
                'episode': episode['episode'],
                'marked_at': int(time.time()),
                'type': 1 if episode['playcount'] else 0,
            })
    return episodes_for_tvmaze


def send_all_episodes_to_tvmaze():
    # type: () -> None
    """
    Fetch the list of all episodes from medialibrary and send watched statuses to TVmaze
    """
    logger.info('Sending all episodes info to TVmaze')
    with background_progress_dialog(_('TVmaze Scrobbler'), _('Updating episodes')) as dialog:
        try:
            tv_shows = get_tvshows()
        except NoDataError:
            logger.warning('Medialibrary has no TV shows')
            return
        logger.debug('TV shows from Kodi:\n{}'.format(pformat(tv_shows)))
        shows_count = len(tv_shows)
        for n, show in enumerate(tv_shows, 1):
            percent = int(100 * n / shows_count)
            message = _('Updating episodes for show \"{}\": {}/{}').format(
                show_name=show['label'],
                count=n,
                total=shows_count
            )
            dialog.update(percent, _('TVmaze Scrobbler'), message)
            unique_id = _get_unique_id(show['uniqueid'])
            if unique_id is None:
                logger.warning(
                    'Unable to determine unique id from show info: {}'.format(pformat(show)))
                continue
            try:
                episodes = get_episodes(show['tvshowid'])
            except NoDataError:
                logger.warning('TV show "{}" has no episodes'.format(show['label']))
                continue
            logger.debug('"{}" episodes from Kodi:\n{}'.format(show['label'], episodes))
            episodes_for_tvmaze = _prepare_episode_list(episodes)
            logger.debug(
                '"{}" episodes for TVmaze:\n{}'.format(show['label'], pformat(episodes_for_tvmaze)))
            show_id, provider = unique_id
            try:
                send_episodes(episodes_for_tvmaze, show_id, provider)
            except UpdateError as exc:
                logger.error(
                    'Unable to update episodes for show "{}": {}'.format(show['label'], exc))
                continue
