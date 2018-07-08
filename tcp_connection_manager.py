"""
This file defined TCPConnectionManager class which handles TCP communication
with hJOPserver. It creates instance of ReportManager in __init___ and calls
its methods based on received data.
"""

import logging
import os
import socket
import time
from collections import deque
from os import path
import traceback

import message_parser
import report_manager
import soundset_manager


class TCPCommunicationEstablishedError(Exception):
    pass


class TCPTimeoutError(OSError):
    pass


class OutdatedVersionError(Exception):
    pass


class SambaNotDefined(Exception):
    pass


class TCPConnectionManager:
    def __init__(self, ip, port, device_info):
        self.device_info = device_info
        self.rm = report_manager.ReportManager(self.device_info)

        self._connect(ip, port)
        self._send('-;HELLO;1.0')
        self._listen()

    def _listen(self):
        previous = ''

        try:
            while self.socket:
                recv = previous + \
                       self.socket.recv(2048).decode('utf-8').replace('\r', '')

                if '\n' not in recv:
                    continue

                q = deque(recv.splitlines(keepends=True))
                self.gong_played = False

                while q:
                    item = q.popleft()
                    logging.debug("> {0}".format(item.strip()))

                    if item.endswith('\n'):
                        try:
                            self._process_message(item.strip())
                        except Exception as e:
                            logging.warning("Message processing error: "
                                            "{0}!".format(str(e)) + '\n' + traceback.print_exc())
                    else:
                        previous = item

                if self.gong_played:
                    self.rm.play_raw_report([os.path.join("gong", "gong_end")])

        except Exception as e:
            logging.error("Connection error: {0}".format(e))

    def _send(self, message):
        try:
            if self.socket:
                logging.debug("< {0}".format(message))
                self.socket.send((message + '\n').encode('UTF-8'))

        except Exception as e:
            logging.error("Connection exception: {0}".format(e))

    def _process_message(self, message):
        parsed = message_parser.parse(message, [';'])
        if len(parsed) < 2:
            return

        parsed[1] = parsed[1].upper()

        if parsed[1] == 'HELLO':
            self._process_hello(parsed)
            self._send(self.device_info.area + ";SH;REGISTER;" +
                      self.rm.soundset.name + ";1.0")

        if parsed[1] != 'SH':
            return

        parsed[2] = parsed[2].upper()

        if parsed[2] == "REGISTER-RESPONSE":
            self._process_register_response(parsed)
        elif parsed[2] == "SYNC":
            self._sync(parsed)
        elif parsed[2] == "CHANGE-SET":
            self._change_set(parsed)
        elif parsed[2] == "SETS-LIST":
            self._process_sets_list()
        elif parsed[2] == "SPEC":
            self.rm.process_spec_message(parsed[3].upper())
        elif parsed[2] == "PRIJEDE" or parsed[2] == "ODJEDE" or parsed[2] == "PROJEDE":
            if not self.gong_played and self.rm.soundset.play_gong:
                self.rm.play_raw_report([
                    os.path.join("gong", "gong_start"),
                    os.path.join("salutation", "vazeni_cestujici")
                ])
                self.gong_played = True

            self.rm.process_trainset_message(parsed)

    def _process_hello(self, parsed):
        version = float(parsed[2])
        logging.info("Server version: {0}.".format(version))

        if version < 1:
            raise OutdatedVersionError("Outdated version of server protocol: "
                                       "{0}!".format(version))

    def _process_register_response(self, parsed):
        state = parsed[3].upper()

        if state == 'OK':
            logging.info("Successfully registered to "
                         "{0}.".format(self.device_info.area))

        elif state == 'ERR':
            error_note = parsed[4].upper()
            logging.error("Register error: {0}".format(error_note))
            # TODO: what to do here?
        else:
            logging.error("Invalid state: {0}!".format(state))
            # TODO: what to do here?

    def _connect(self, ip, port):
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(50)
            self.socket.connect((ip, port))
        except Exception as e:
            logging.warning("Connect exception: {0}".format(e))
            self.socket = None

    def _process_sets_list(self):
        sound_sets = soundset_manager.get_local_sets_list(
            self.device_info.soundset_path
        )

        if self.device_info.smb_server and self.sevice_info.smb_folder:
            sound_sets += soundset_manager.get_samba_sets_list(
                self.device_info.smb_server,
                self.device_info.smb_home_folder
            )

        self._send(
            self.device_info.area + ';SH;SETS-LIST;{' +
            ','.join(set(sound_sets)) + '}'
        )
