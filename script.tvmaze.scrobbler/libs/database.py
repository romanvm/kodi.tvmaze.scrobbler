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
# pylint: disable=missing-docstring
"""
The scrobbler database API
"""
from __future__ import absolute_import, unicode_literals

import os
import sqlite3

from .kodi_service import ADDON_PROFILE_DIR

try:
    from typing import Optional, Text  # pylint: disable=unused-import
except ImportError:
    pass


class DbTable(object):
    DB = os.path.join(ADDON_PROFILE_DIR, 'tvmaze.sqlite')

    def __init__(self):
        self._connection = sqlite3.connect(self.DB)
        self._cursor = None  # type: Optional[sqlite3.Cursor]
        self._create_table()

    def _create_table(self):
        raise NotImplementedError

    def __enter__(self):
        self._cursor = self._connection.cursor()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._connection.commit()
        self._connection.close()


class PulledEpisodesTable(DbTable):
    """
    The table of pulled episodes

    It is used to prevent extra push of a watched episode which has just been pulled from TVmaze.
    """

    def _create_table(self):
        self._connection.execute("""
            CREATE TABLE IF NOT EXISTS pulled_episodes(
                episode_id INTEGER PRIMARY KEY,
                timestamp INTEGER NOT NULL
            )
        """)

    def upsert_episode(self, episode_id):
        # type: (int) -> None
        self._cursor.execute("""
            SELECT 1
            FROM pulled_episodes
            WHERE episode_id = ?
        """, [episode_id])
        row = self._cursor.fetchone()
        if not row:
            self._cursor.execute("""
                INSERT INTO pulled_episodes
                (episode_id, timestamp)
                VALUES (?, STRFTIME('%s', 'now'))
            """, [episode_id])
        else:
            self._cursor.execute("""
                UPDATE pulled_episodes
                SET timestamp = STRFTIME('%s', 'now')
                WHERE episode_id = ?
            """, [episode_id])

    def is_pulled(self, episode_id):
        # type: (int) -> bool
        self._cursor.execute("""
            SELECT 1
            FROM pulled_episodes
            WHERE episode_id = ? AND STRFTIME('%s', 'now') - timestamp < 10
        """, [episode_id])
        row = self._cursor.fetchone()
        return bool(row)


class TimeLastUpdatedTable(DbTable):

    def _create_table(self):
        self._connection.execute("""
            CREATE TABLE IF NOT EXISTS time_last_updated(
                last_updated TEXT NOT NULL
            )
        """)

    def upsert_time_updated(self, time_string):
        # type: (Text) -> None
        self._cursor.execute("""
            SELECT last_upated
            FROM time_last_updated
            LIMIT 1
        """)
        row = self._cursor.fetchone()
        if not row:
            self._cursor.execute("""
                INSERT INTO time_last_updated
                (last_updated)
                VALUES (?)
            """, [time_string])
        else:
            self._cursor.execute("""
                UPDATE time_last_updated
                SET last_upated = ?
            """, [time_string])

    def get_time_updated(self):
        # type: () -> Optional[Text]
        self._cursor.execute("""
            SELECT last_upated
            FROM time_last_updated
            LIMIT 1
        """)
        row = self._cursor.fetchone()
        if row:
            return row[0]
        return None
