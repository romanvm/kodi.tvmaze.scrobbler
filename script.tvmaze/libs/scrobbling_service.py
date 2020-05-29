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

"""Scraper actions"""
# pylint: disable=missing-docstring
from __future__ import absolute_import, division, unicode_literals

import os
import re
import time
import uuid
from pprint import pformat

import pyqrcode
from kodi_six import xbmc

from .gui import DIALOG, ConfirmationDialog, background_progress_dialog
from .kodi_service import ADDON, ADDON_ID, PROFILE_DIR, ICON, GETTEXT, logger
from .medialibrary_api import (NoDataError, get_tvshows, get_episodes, get_tvshow_details,
                               get_episode_details)
from .tvmaze_api import AuthorizationError, UpdateError, start_authorization, send_episodes

try:
    from typing import Text, Dict, Any, List, Tuple  # pylint: disable=unused-import
except ImportError:
    pass

_ = GETTEXT

SUPPORTED_IDS = ('tvmaze', 'tvdb', 'imdb')


class StatusType(object):  # pylint: disable=too-few-public-methods
    WATCHED = 0
    ACQUIRED = 1
    SKIPPED = 2


def _get_unique_id(unique_ids):
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


def _prepare_episode_list(kodi_episode_list):
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


def authorize_addon():
    # type: () -> None
    """
    Authorize the addon on TVmaze

    The function sends authorization request to TVmaze and saves TVmaze
    username and API token for scrobbling requests authorization
    """
    old_username = ADDON.getSettingString('username')
    old_apikey = ADDON.getSettingString('apikey')
    if old_username and old_apikey:
        answer = DIALOG.yesno(
            _('TVmaze Scrobbler'),
            _('The addon is already authorized.[CR]Authorize again?')
        )
        if not answer:
            return
    keyboard = xbmc.Keyboard(heading=_('Your TVmaze account email'))
    keyboard.doModal()
    if keyboard.isConfirmed():
        email = keyboard.getText()
        if re.search(r'^[\w.\-+]+@[\w.-]+\.[\w]+$', email) is None:
            logger.error('Invalid email: {}'.format(email))
            DIALOG.notification(ADDON_ID, _('Invalid email'), icon='error', time=3000)
            return
        try:
            token, confirm_url = start_authorization(email)
        except AuthorizationError as exc:
            logger.error('TVmaze authorization error: {}'.format(exc))
            message = _('Authorization error: {}').format(exc)
            DIALOG.notification(ADDON_ID, message, icon='error')
            return
        qrcode_filename = uuid.uuid4().hex + '.png'
        qrcode_path = os.path.join(PROFILE_DIR, qrcode_filename)
        qrcode_image = pyqrcode.create(confirm_url)
        qrcode_image.png(qrcode_path, scale=10)
        confirmation_dialog = ConfirmationDialog(email, token, confirm_url, qrcode_path)
        confirmation_dialog.doModal()
        if confirmation_dialog.is_confirmed:
            ADDON.setSettingString('username', confirmation_dialog.username)
            ADDON.setSettingString('apikey', confirmation_dialog.apikey)
            DIALOG.notification(ADDON_ID, _('Addon has been authorized successfully'),
                                icon=ICON, sound=False, time=3000)
        elif confirmation_dialog.error_message is not None:
            logger.error('Confirmation error: {}'.format(confirmation_dialog.error_message))
            message = _('Confirmation error: {}').format(confirmation_dialog.error_message)
            DIALOG.notification(ADDON_ID, message, icon='error')
        del confirmation_dialog


def send_all_episodes_to_tvmaze():
    # type: () -> None
    """
    Fetch the list of all episodes from medialibrary and send watched statuses to TVmaze
    """
    logger.info('Syncing all episodes info to TVmaze...')
    errors = False
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
            message = _(r'Updating episodes for show \"{show_name}\": {count}/{total}').format(
                show_name=show['label'],
                count=n,
                total=shows_count
            )
            dialog.update(percent, _('TVmaze Scrobbler'), message)
            try:
                show_id, provider = _get_unique_id(show['uniqueid'])
            except LookupError:
                logger.error(
                    'Unable to determine unique id from show info: {}'.format(pformat(show)))
                continue
            try:
                episodes = get_episodes(show['tvshowid'])
            except NoDataError:
                logger.warning('TV show "{}" has no episodes'.format(show['label']))
                continue
            logger.debug('"{}" episodes from Kodi:\n{}'.format(show['label'], pformat(episodes)))
            episodes_for_tvmaze = _prepare_episode_list(episodes)
            logger.debug(
                '"{}" episodes for TVmaze:\n{}'.format(show['label'], pformat(episodes_for_tvmaze)))
            try:
                send_episodes(episodes_for_tvmaze, show_id, provider)
            except UpdateError as exc:
                errors = True
                logger.error(
                    'Unable to update episodes for show "{}": {}'.format(show['label'], exc))
                continue
    if errors:
        DIALOG.notification(ADDON_ID, _('Update completed with errors'), icon='error')
    else:
        DIALOG.notification(ADDON_ID, _('Update completed'), icon=ICON, time=3000, sound=False)


def update_single_episode(episode_id):
    # type: (int) -> None
    """Update watched status for a single episode"""
    episode_details = get_episode_details(episode_id)
    tvshow_details = get_tvshow_details(episode_details['tvshowid'])
    try:
        unique_id, provider = _get_unique_id(tvshow_details['uniqueid'])
    except LookupError:
        logger.error(
            'Unable to determine unique id from show info: {}'.format(pformat(tvshow_details)))
        return
    episodes_for_tvmaze = _prepare_episode_list([episode_details])
    try:
        send_episodes(episodes_for_tvmaze, unique_id, provider)
    except UpdateError as exc:
        logger.error('Failed to update episode status:\n{}Error: {}'.format(episode_details, exc))
        DIALOG.notification(ADDON_ID, _('Failed to update episode status'), icon='error')
    else:
        DIALOG.notification(
            ADDON_ID, _('Episode status updated'), icon=ICON, time=3000, sound=False)
