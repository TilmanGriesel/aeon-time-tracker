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

from ReaderService import *
from TimeEntryManager import *
import logging

logger = logging.getLogger(__name__)
reader_service = ReaderService()
time_entry_manager = TimeEntryManager()


def initialize_reader():
    reader_service.onInserted += on_reader_card_inserted
    ok, ex = reader_service.initialize()
    if ok:
        logger.info("Reader successful initialized.")
    else:
        logger.error(ex.message)


def on_reader_card_inserted(cid):
    try:
        logger.info("Card detected. CID: " + cid)
        result = time_entry_manager.add_entry(cid)

        # Handle entry addition result
        if result.action is EntryAction.CHECK_IN:
            if result.inconsistent:
                reader_service.trigger_reader_check_in_warn(True)
            else:
                reader_service.trigger_reader_check_in(True)
        elif result.action is EntryAction.CHECK_OUT:
            reader_service.trigger_reader_check_out(True)

        # Everything went fine, commit changes to db
        time_entry_manager.finalise_entry(True)
        logger.info("Successfully created entry [" + result.action +
                    "] for card CID: " + cid +
                    " UID: " + str(result.user["id"]))
    except Exception as ex:
        if type(ex) is InvalidCardException:
            logger.info("Invalid card detected. CID: " + cid)
            reader_service.trigger_reader_invalid()
        elif type(ex) is ReaderCommandException:
            logger.info(
                "Aborting entry creation for CID: " + cid + ", it seems that the user removed the card to quick.")
        else:
            logger.error("Failed to create entry! Message: " + ex.message + " CID: " + cid)
            reader_service.trigger_reader_error()
        # Rollback db changes
        time_entry_manager.finalise_entry(False)
        return


def main():
    logging.basicConfig(format='%(levelname)s [%(name)s]: %(message)s', level=logging.DEBUG)
    # logging.basicConfig(filename='app.log', level=logging.INFO)
    logging.info('Started')
    initialize_reader()


if __name__ == '__main__':
    main()

raw_input("\nPress Enter to exit ...\n")