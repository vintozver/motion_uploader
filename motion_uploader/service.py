# -*- coding: utf-8 -*-

import typing
import os
import stat
import datetime
import dateutil.relativedelta
import signal
import logging
from threading import Event
import http
import http.client as http_client
import urllib.parse as url_parser
import json
import re
import time
from .config import Config
from .logging_defaults import *


class SignalReceived(Exception):
    pass


class FetchAccessTokenError(Exception):
    pass


class Service(object):
    def __init__(self):
        self.root_path = os.getcwd()
        self.cf = Config()
        self.camera_id = self.cf.get_camera_id()
        self.re_file = re.compile('^(\\d{8})(.*\\.jpg)$', re.UNICODE | re.IGNORECASE)
        self.access_token_type = None
        self.access_token = None
        self.access_token_expires = None

    def fetch_access_token(self) -> bool:
        # Convert the refresh_token to the access_token
        http_conn = http_client.HTTPSConnection('login.microsoftonline.com')
        http_conn.request(
            'POST', '/common/oauth2/v2.0/token',
            url_parser.urlencode({
                'client_id': self.cf.get_client_id(),
                'redirect_uri': self.cf.get_redirect_uri(),
                'client_secret': self.cf.get_client_secret(),
                'refresh_token': self.cf.get_refresh_token(),
                'grant_type': 'refresh_token',
            }),
            {
                'Content-Type': 'application/x-www-form-urlencoded',
            }
        )
        http_resp = http_conn.getresponse()
        if http_resp.status == http.HTTPStatus.OK.value:
            tokens_obj = json.loads(http_resp.read().decode('utf-8'))
            logging.info('Tokens: %s' % tokens_obj)
            self.access_token_type = tokens_obj['token_type']
            self.access_token = tokens_obj['access_token']
            self.access_token_expires = datetime.datetime.utcnow() + \
                dateutil.relativedelta.relativedelta(seconds=int(tokens_obj['expires_in']))
            return True
        else:
            logging.error('Unexpected response: %s %s\n%s' % (
                http_resp.status,
                http_resp.reason,
                http_resp.read().decode('utf-8', errors='replace')
            ))
            return False

    def fetch_access_token_retry(self):
        for counter in range(0, 3):
            if self.fetch_access_token():
                return
        raise FetchAccessTokenError()

    def process_files(self, limit: int=10) -> bool:
        if self.access_token is None or self.access_token_expires is None or \
                self.access_token_expires <= datetime.datetime.utcnow():
            self.fetch_access_token_retry()

        potential_files = list()
        dt = datetime.datetime.utcnow()
        dt_delayfile = dt - dateutil.relativedelta.relativedelta(seconds=5)  # don't include files younger than 5sec
        for file_name in os.listdir(self.root_path):
            file_match = self.re_file.match(file_name)
            if file_match is None:
                continue  # only inlude the matched names
            file_stat = os.stat(os.path.join(self.root_path, file_name))
            if not stat.S_ISREG(file_stat.st_mode):
                continue  # file is not regular
            file_dt = datetime.datetime.fromtimestamp(file_stat.st_mtime)
            if file_dt >= dt_delayfile:
                continue  # only include the files older than the delay specified
                # this will fix the problem with the disk write delay (files may be still written)

            potential_files.append((
                file_match.group(1),  # filename: date "%Y%m%d"
                file_match.group(2),  # filename: time and the rest
                file_name,  # full filename
                file_dt,
            ))
        # sort by dt, newest first
        processing_files = sorted(potential_files, key=lambda potential_file: potential_file[3], reverse=True)[:limit]
        if len(potential_files) > len(processing_files):
            more_files = True
        else:
            more_files = False
        logging.info('Potential files: %d, to process: %d' % (len(potential_files), len(processing_files)))
        # no longer needed, at this time
        del potential_files

        for processing_file in processing_files:
            if self.upload_file(
                    processing_file[0],
                    processing_file[1],
                    open(os.path.join(self.root_path, processing_file[2]), 'rb')
            ):
                try:
                    os.unlink(os.path.join(self.root_path, processing_file[2]))
                except OSError:
                    pass
            else:
                time.sleep(30)  # error cool down period

        return more_files

    def upload_file(self, directory: str, name: str, contents: typing.BinaryIO) -> bool:
        http_conn = http_client.HTTPSConnection('graph.microsoft.com')
        http_conn.request(
            'PUT',
            '/v1.0/me/drive/root:%s:/content' % os.path.join('/motion_uploader', self.camera_id, directory, name),
            contents.read(),
            {
                'Authorization': '%s %s' % (self.access_token_type, self.access_token),
                'Content-Type': 'image/jpeg',
            }
        )
        http_resp = http_conn.getresponse()
        if http_resp.status == http.HTTPStatus.CREATED.value or http_resp.status == http.HTTPStatus.OK.value:
            driveitem_obj = json.loads(http_resp.read().decode('utf-8'))
            logging.info('Uploaded file: %s' % driveitem_obj)
            return True
        else:
            logging.error('Unexpected response: %s %s\n%s' % (
                http_resp.status,
                http_resp.reason,
                http_resp.read().decode('utf-8', errors='replace')
            ))
            return False

    def create_folders(self):
        if self.access_token is None or self.access_token_expires is None or \
                self.access_token_expires <= datetime.datetime.utcnow():
            self.fetch_access_token_retry()

        http_conn = http_client.HTTPSConnection('graph.microsoft.com')

        # create root dir
        http_conn.request(
            'POST', '/v1.0/me/drive/root/children',
            json.dumps({
                'name': 'motion_uploader',
                'folder': {},
                '@microsoft.graph.conflictBehavior': 'fail',
            }),
            {
                'Authorization': '%s %s' % (self.access_token_type, self.access_token),
                'Content-Type': 'application/json',
            }
        )
        http_resp = http_conn.getresponse()
        if http_resp.status == http.HTTPStatus.CREATED.value:
            driveitem_obj = json.loads(http_resp.read().decode('utf-8'))
            logging.info('Created dir: %s' % driveitem_obj)
        elif http_resp.status == http.HTTPStatus.CONFLICT.value:
            logging.info('Conflict: %s' % http_resp.read().decode('utf-8', errors='replace'))
        else:
            logging.error('Unexpected response: %s %s\n%s' % (
                http_resp.status,
                http_resp.reason,
                http_resp.read().decode('utf-8', errors='replace')
            ))
            return False

        # create camera dir
        http_conn.request(
            'POST', '/v1.0/me/drive/root/motion_uploader/children',
            json.dumps({
                'name': self.camera_id,
                'folder': {},
                '@microsoft.graph.conflictBehavior': 'fail',
            }),
            {
                'Authorization': '%s %s' % (self.access_token_type, self.access_token),
                'Content-Type': 'application/json',
            }
        )
        http_resp = http_conn.getresponse()
        if http_resp.status == http.HTTPStatus.CREATED.value:
            driveitem_obj = json.loads(http_resp.read().decode('utf-8'))
            logging.info('Created dir: %s' % driveitem_obj)
        elif http_resp.status == http.HTTPStatus.CONFLICT.value:
            logging.info('Conflict: %s' % http_resp.read().decode('utf-8', errors='replace'))
        else:
            logging.error('Unexpected response: %s %s\n%s' % (
                http_resp.status,
                http_resp.reason,
                http_resp.read().decode('utf-8', errors='replace')
            ))
            return False

        # all done
        return True


def main():
    logging.info('Running as a service')

    service = Service()

    def signal_handler(signum, frame):
        logging.warning('Received signal %s. Exiting' % signum)
        raise SignalReceived(signum)

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGHUP, signal_handler)
    signal.signal(signal.SIGALRM, signal_handler)

    signal.alarm(30)
    service.create_folders()

    try:
        processing_limit = 10
        while True:
            signal.alarm(processing_limit * 30 + 5)  # set the alarm so the process is terminated if hung
            if not service.process_files(processing_limit):
                time.sleep(5)
                logging.info('Status: alive')
    except SignalReceived:
        logging.warning('Interrupt received. Shutting down ...')


if __name__ == '__main__':
    exit(main())
