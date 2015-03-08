# The MIT License (MIT)
#
# Copyright (c) 2015 Tilman Griesel
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import sqlite3
import datetime
from dateutil import parser
import math


class EntryAction:
    CHECK_IN = "check_in"
    CHECK_OUT = "check_out"

    def __init__(self):
        return


class TimeEntryManager:
    DB_NAME = 'aeon.db'

    def __init__(self, min_round=5, min_redundancy_lock=10):
        self.min_round = min_round
        self.min_redundancy_lock = min_redundancy_lock
        self.conn = sqlite3.connect(self.DB_NAME, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.c = self.conn.cursor()

    def add_entry(self, cid):
        """
        Add a new entry to the database.
        :param cid: Card ID
        :return:
        """
        user = self.get_user_for_card(cid)
        if user is None:
            raise InvalidCardException("Invalid card. CID: " + cid)

        # Get last time tracking entry
        last_entry = self.get_last_entry(cid, user)

        # Define action
        action = EntryAction.CHECK_IN
        inconsistent = False
        last_datetime = None
        invalidated = False

        # Determine action type and check for "last day
        # inconsistency" aka. user checked not out properly
        if last_entry is not None:
            last_datetime = parser.parse(last_entry["datetime"])
            if last_entry["action"] == EntryAction.CHECK_IN:
                if last_datetime < self.get_start_of_day():
                    inconsistent = True
                if last_datetime >= self.get_start_of_day():
                    action = EntryAction.CHECK_OUT

        # Get current time and floor it if the user checks in
        # or ceil it if the user checks out
        current_time = self.round_time(self.get_current_time(), self.min_round, action == EntryAction.CHECK_OUT)

        # Revert last entry if the requested action is in the
        # reversion time span
        if last_datetime is not None:
            if last_datetime > current_time:
                time_diff = last_datetime - current_time
            else:
                time_diff = current_time - last_datetime
            if time_diff < datetime.timedelta(minutes=self.min_redundancy_lock):
                invalidated = True
                self.c.execute("UPDATE tracking SET valid=0 WHERE id=:id",
                               {"id": last_entry["id"]})

        # Insert new data set with determined values
        if not invalidated:
            self.c.execute(
                "INSERT INTO tracking(realdatetime, datetime, uid, cid, action, valid) VALUES (datetime('now'), :datetime, :uid, :cid, :action, :valid)",
                {"datetime": current_time, "uid": user["id"], "cid": cid, "action": action, "valid": True})

        return EntryResult(user, action, inconsistent)


    def finalise_entry(self, commit):
        """
        Commit or rollback the last database entry.
        :param commit: If True the last change will written to the db else the last entry will be ignored.
        :return:
        """
        if commit:
            self.conn.commit()
        else:
            self.conn.rollback()

    def get_user_for_card(self, cid):
        self.c.execute(
            "SELECT * FROM users WHERE " +
            "id=(SELECT uid FROM cards WHERE cid=:cid AND active=1 LIMIT 1) AND active=1 LIMIT 1",
            {"cid": cid})
        row = self.c.fetchone()
        return row

    def get_last_entry(self, cid, user=None):
        if user is None:
            user = self.get_user_for_card(cid)

        if user is not None:
            self.c.execute("SELECT * FROM tracking WHERE uid=:uid AND valid=1 ORDER BY id DESC LIMIT 1",
                           {"uid": user["id"]})
            row = self.c.fetchone()
            return row
        return None

    def get_current_time(self):
        self.c.execute("SELECT datetime('now')")
        row = self.c.fetchone()
        return parser.parse(row[0])

    def get_start_of_day(self):
        self.c.execute("SELECT datetime('now', 'start of day')")
        row = self.c.fetchone()
        return parser.parse(row[0])

    def round_time(self, tm, min, up):
        if up:
            mins = math.ceil(float(tm.minute) / min) * min
        else:
            mins = math.floor(float(tm.minute) / min) * min
        diff_mins = mins - tm.minute
        new_time = tm + datetime.timedelta(minutes=diff_mins)
        new_time = new_time.replace(second=0)
        return new_time


class EntryResult():
    def __init__(self, user, action, inconsistent):
        self.user = user
        self.action = action
        self.inconsistent = inconsistent
        pass


class InvalidCardException(Exception):
    pass