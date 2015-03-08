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

import logging
from smartcard.scard import *
from smartcard.CardMonitoring import CardMonitor, CardObserver
from smartcard.util import *
from EventHook import EventHook


class ReaderCommands:
    CMD_GET_UID = [0xFF, 0xCA, 0x00, 0x00, 0x04]
    CMD_NF_CHECK_IN = [0xFF, 0x00, 0x40, 0xA2, 0x04, 0x01, 0x01, 0x02, 0x01]  # [. .] green
    CMD_NF_CHECK_IN_WARN = [0xFF, 0x00, 0x40, 0xEA, 0x04, 0x02, 0x01, 0x02, 0x01]  # [. .] green red
    CMD_NF_CHECK_OUT = [0xFF, 0x00, 0x40, 0xF3, 0x04, 0x01, 0x01, 0x02, 0x01]  # [. .] orange
    CMD_NF_INVALIDATED = [0xFF, 0x00, 0x40, 0xF3, 0x04, 0x01, 0x01, 0x04, 0x01]  # [. . .] green
    CMD_NF_INVALID = [0xFF, 0x00, 0x40, 0x55, 0x04, 0x03, 0x02, 0x03, 0x01]  # [_ _ _] red
    CMD_NF_ERROR = [0xFF, 0x00, 0x40, 0x55, 0x04, 0x01, 0x01, 0x10, 0x01]  # [. . . . . . . . . .] red

    def __init__(self):
        pass


class ReaderService:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.reader = None
        self.hcontext = None
        self.onInserted = EventHook()

    def initialize(self):
        try:
            hresult, self.hcontext = SCardEstablishContext(SCARD_SCOPE_USER)
            if hresult != SCARD_S_SUCCESS:
                raise Exception('Failed to establish context : ' +
                                SCardGetErrorMessage(hresult))
            self.logger.info('Context established!')

            hresult, readers = SCardListReaders(self.hcontext, [])
            if hresult != SCARD_S_SUCCESS:
                raise Exception('Failed to list readers: ' +
                                SCardGetErrorMessage(hresult))
            self.logger.info('PCSC Readers:' + str(readers))

            if len(readers) < 1:
                raise Exception('No smart card readers')

            self.reader = readers[0]
            self.logger.info("Using reader:" + str(self.reader))

            card_monitor = CardMonitor()
            card_observer = CardObserverDispatcher()
            card_observer.onChange += self.on_card_changed
            card_monitor.addObserver(card_observer)
            self.logger.info("Started card observer ...")

            yield True
            yield None
        except Exception as ex:
            print "Exception:", ex.message
            yield False
            yield ex

    def on_card_changed(self, inserted, card_atr):
        cid = None
        if inserted:
            try:
                hresult, response, hcard = self.trigger_reader_command(ReaderCommands.CMD_GET_UID)
                if len(response) == 6:
                    cid = toHexString(response)
                    cid = cid.replace(" ", "")
                else:
                    raise Exception(
                        "Card UID (CID) length is invalid! Length: " + str(len(response)) + ", Response: " + str(
                            response))
            except Exception as ex:
                self.trigger_reader_error()
                self.logger.error("Failed to read card UID (CID)! Message: " + ex.message)
        if cid is not None:
            self.onInserted.fire(cid)

    def trigger_reader_check_in(self, raise_exceptions=False):
        try:
            hresult, response, hcard = self.trigger_reader_command(ReaderCommands.CMD_NF_CHECK_IN)
        except Exception as ex:
            self.logger.debug("Failed to trigger check in notification: " + ex.message)
            if raise_exceptions:
                raise ex

    def trigger_reader_check_in_warn(self, raise_exceptions=False):
        try:
            hresult, response, hcard = self.trigger_reader_command(ReaderCommands.CMD_NF_CHECK_IN_WARN)
        except Exception as ex:
            self.logger.debug("Failed to trigger check in warn notification: " + ex.message)
            if raise_exceptions:
                raise ex

    def trigger_reader_check_out(self, raise_exceptions=False):
        try:
            hresult, response, hcard = self.trigger_reader_command(ReaderCommands.CMD_NF_CHECK_OUT)
        except Exception as ex:
            self.logger.debug("Failed to trigger check out notification: " + ex.message)
            if raise_exceptions:
                raise ex

    def trigger_reader_invalidated(self, raise_exceptions=False):
        try:
            hresult, response, hcard = self.trigger_reader_command(ReaderCommands.CMD_NF_INVALIDATED)
        except Exception as ex:
            self.logger.debug("Failed to trigger invalidated notification: " + ex.message)
            if raise_exceptions:
                raise ex

    def trigger_reader_invalid(self, raise_exceptions=False):
        try:
            hresult, response, hcard = self.trigger_reader_command(ReaderCommands.CMD_NF_INVALID)
        except Exception as ex:
            self.logger.debug("Failed to trigger invalid notification: " + ex.message)
            if raise_exceptions:
                raise ex

    def trigger_reader_error(self, raise_exceptions=False):
        try:
            hresult, response, hcard = self.trigger_reader_command(ReaderCommands.CMD_NF_ERROR)
        except Exception as ex:
            self.logger.debug("Failed to trigger error notification: " + ex.message)
            if raise_exceptions:
                raise ex

    def trigger_reader_command(self, command):
        hresult, hcard, dw_active_protocol = SCardConnect(self.hcontext, self.reader,
                                                          SCARD_SHARE_SHARED, SCARD_PROTOCOL_T0 | SCARD_PROTOCOL_T1)

        if hresult != SCARD_S_SUCCESS:
            raise ReaderCommandException('Unable to connect: ' +
                                         SCardGetErrorMessage(hresult))

        hresult, response = SCardTransmit(hcard, dw_active_protocol, command)
        if hresult != SCARD_S_SUCCESS:
            raise ReaderCommandException('Unable to transmit command: ' +
                                         SCardGetErrorMessage(hresult))

        yield hresult
        yield response
        yield hcard


class CardObserverDispatcher(CardObserver):
    def __init__(self, *args, **kwargs):
        CardObserver.__init__(self, *args, **kwargs)
        self.onChange = EventHook()

    def update(self, observable, (addedcards, removedcards)):
        for card in addedcards:
            self.onChange.fire(True, card.atr)
        for card in removedcards:
            self.onChange.fire(False, card.atr)


class ReaderCommandException(Exception):
    pass