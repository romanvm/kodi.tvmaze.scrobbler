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

"""GUI-related classes and functions"""
# Todo: Add localization support
from __future__ import absolute_import, unicode_literals

import os
import re
import threading
import uuid
import weakref

import pyxbmct
import qrcode
from kodi_six import xbmc
from kodi_six.xbmcgui import Dialog
from six import text_type

from .kodi_service import ADDON, ADDON_ID, PROFILE_DIR
from .tvmaze_api import start_authorization, poll_authorization, AuthorizationError

try:
    from typing import Text  # pylint: disable=unused-import
except ImportError:
    pass

DIALOG = Dialog()


class ConfirmationLoop(threading.Thread):
    # pylint: disable=missing-docstring
    def __init__(self, parent_window, token):
        # type: (ConfirmationDialog, Text) -> None
        super(ConfirmationLoop, self).__init__()
        self._parent_window = weakref.proxy(parent_window)  # type: ConfirmationDialog
        self._token = token
        self._monitor = xbmc.Monitor()
        self.username = ''
        self.apikey = ''
        self.error_message = None
        self.stop_event = threading.Event()

    def run(self):
        self.stop_event.clear()
        while not self.stop_event.is_set():
            xbmc.sleep(5000)
            if self._monitor.abortRequested():
                break
            try:
                result = poll_authorization(self._token)
            except AuthorizationError as exc:
                self.error_message = text_type(exc)
                break
            else:
                if result is None:
                    continue
                self.username, self.apikey = result
                break
        self._parent_window.close()


class ConfirmationDialog(pyxbmct.AddonDialogWindow):
    # pylint: disable=missing-docstring
    def __init__(self, email, token, confirm_url, qrcode_path):
        # type: (Text, Text, Text, Text) -> None
        super(ConfirmationDialog, self).__init__('Confirm Authorization')
        self._email = email
        self._confirm_url = confirm_url
        self._qrcode_path = qrcode_path
        self.is_confirmed = False
        self.username = ''
        self.apikey = ''
        self.error_message = None
        self._confirmation_loop = ConfirmationLoop(self, token)
        self.setGeometry(500, 200, 5, 2)  # Todo: needs to be adjusted
        self._set_controls()
        self._set_connections()

    def _set_controls(self):
        textbox = pyxbmct.TextBox()
        self.placeControl(textbox, 0, 0, 2, 2)
        textbox.setText(
            'Please check your {email} mailbox for an authorization link[CR]'
            'or visit the address below to authorize the addon:[CR]{confirm_url}'.format(
                email=self._email,
                confirm_url=self._confirm_url
            )
        )
        qr_code = pyxbmct.Image(self._qr_code_path)
        self.placeControl(qr_code, 2, 2, 2, 2)
        self._cancel_btn = pyxbmct.Button('Cancel')
        self.placeControl(self._cancel_btn, 4, 0, 2)
        self.setFocus(self._cancel_btn)

    def _set_connections(self):
        self.connect(pyxbmct.ACTION_NAV_BACK, self.close)
        self.connect(self._cancel_btn, self.close)

    def doModal(self):
        self._confirmation_loop.start()
        super(ConfirmationDialog, self).doModal()
        self.username = self._confirmation_loop.username
        self.apikey = self._confirmation_loop.apikey
        self.username = self._confirmation_loop.username
        if self.username and self.apikey and self.error_message is None:
            self.is_confirmed = True

    def close(self):
        self.is_confirmed = False
        self._confirmation_loop.stop_event.set()
        self._confirmation_loop.join()
        super(ConfirmationDialog, self).close()


def authorize_addon():
    """
    Authorize the addon on TVmaze

    The function sends authorization request to TVmaze and saves TVmaze
    username and API token for scrobbling requests authorization
    """
    old_username = ADDON.getSettingString('username')
    old_apikey = ADDON.getSettingString('apikey')
    if old_username and old_apikey:
        answer = DIALOG.yesno(
            'TVmaze Scrobbler',
            'The addon is already authorized.[CR]Authorize again?'
        )
        if not answer:
            return
    keyboard = xbmc.Keyboard(heading='Your TVmaze account email')
    keyboard.doModal()
    if keyboard.isConfirmed():
        email = keyboard.getText()
        if re.search(r'^[\w.\-+]+@[\w.-]+\.[\w]+$', email) is None:
            DIALOG.notification(ADDON_ID, 'Please enter a valid email', icon='error', time=3000)
            return
        try:
            token, confirm_url = start_authorization(email)
        except AuthorizationError as exc:
            message = 'Authorization error: {}'.format(exc)
            DIALOG.notification(ADDON_ID, message, icon='error')
            return
        qrcode_filename = uuid.uuid4().hex + '.png'
        qrcode_path = os.path.join(PROFILE_DIR, qrcode_filename)
        qrcode_image = qrcode.make(confirm_url)
        with open(qrcode_path, 'wb') as fo:
            qrcode_image.save(fo)
        conformation_dialog = ConfirmationDialog(email, token, confirm_url, qrcode_path)
        conformation_dialog.doModal()
        if conformation_dialog.is_confirmed:
            ADDON.setSettingString('username', conformation_dialog.username)
            ADDON.setSettingString('apikey', conformation_dialog.apikey)
        elif conformation_dialog.error_message is not None:
            message = 'Confirmation error: {}'.format(conformation_dialog.error_message)
            DIALOG.notification(ADDON_ID, message, icon='error')
        del conformation_dialog


MAIN_GUI_FUNCTIONS = {
    0: authorize_addon,
}


def main_gui():
    """Main scrobbler GUI"""
    monitor = xbmc.Monitor()
    while not monitor.abortRequested():
        result = DIALOG.select('TVmaze Scrobbler', ['Authorize the addon'])
        func = MAIN_GUI_FUNCTIONS.get(result)
        if func is None:
            break
        func()
