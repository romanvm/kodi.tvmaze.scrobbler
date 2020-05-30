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

"""Script entry point"""

from __future__ import absolute_import, unicode_literals

from kodi_six import xbmcgui

from libs.kodi_service import debug_exception, GETTEXT
from libs.scrobbling_service import (authorize_addon, send_all_episodes_to_tvmaze,
                                     update_recent_episodes)

_ = GETTEXT

ACTIONS = {
    0: send_all_episodes_to_tvmaze,
    1: update_recent_episodes,
    2: authorize_addon,
}


def main():
    """Main scrobbler menu"""
    result = xbmcgui.Dialog().select(_('TVmaze Scrobbler Menu'), [
        _('Update all shows'),
        _('Update recent episodes'),
        _('Authorize the addon'),
    ])
    if result >= 0:
        action = ACTIONS[result]
        action()


if __name__ == '__main__':
    with debug_exception():
        main()
