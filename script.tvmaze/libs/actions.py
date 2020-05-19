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
import uuid
from pprint import pformat

import pyqrcode
from kodi_six import xbmc, xbmcgui

from .gui import ConfirmationDialog, background_progress_dialog
from .kodi_service import ADDON, ADDON_ID, PROFILE_DIR, ICON, GETTEXT, logger
from .medialibrary_api import NoDataError, get_tvshows, get_episodes
from .scrobbling_service import get_unique_id, prepare_episode_list
from .tvmaze_api import AuthorizationError, UpdateError, start_authorization, send_episodes

_ = GETTEXT

DIALOG = xbmcgui.Dialog()


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
                show_id, provider = get_unique_id(show['uniqueid'])
            except LookupError:
                logger.warning(
                    'Unable to determine unique id from show info: {}'.format(pformat(show)))
                continue
            try:
                episodes = get_episodes(show['tvshowid'])
            except NoDataError:
                logger.warning('TV show "{}" has no episodes'.format(show['label']))
                continue
            logger.debug('"{}" episodes from Kodi:\n{}'.format(show['label'], pformat(episodes)))
            episodes_for_tvmaze = prepare_episode_list(episodes)
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
        DIALOG.notification(ADDON_ID, _('Update finished with errors'), icon='error')
    else:
        DIALOG.notification(ADDON_ID, _('Update finished'), icon=ICON, sound=False)
