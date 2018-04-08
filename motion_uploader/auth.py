# -*- coding: utf-8 -*-

import logging
import http
import http.client as http_client
import urllib.parse as url_parser
import json
from .config import Config
from .logging_defaults import *


def main():
    cf = Config()

    # Ask to visit the URI, get the code
    authorize_uri = url_parser.urlunsplit((
        'https', 'login.microsoftonline.com', '/common/oauth2/v2.0/authorize',
        url_parser.urlencode({
            'client_id': cf.get_client_id(),
            'scope': 'offline_access files.readwrite',
            'response_type': 'code',
            'redirect_uri': cf.get_redirect_uri(),
        }), ''
    ))
    print('URI: %s' % authorize_uri)
    code = input('Code from the redirect URI: ')

    # Convert the code to the refresh_token
    http_conn = http_client.HTTPSConnection('login.microsoftonline.com')
    http_conn.request(
        'POST', '/common/oauth2/v2.0/token',
        url_parser.urlencode({
            'client_id': cf.get_client_id(),
            'redirect_uri': cf.get_redirect_uri(),
            'client_secret': cf.get_client_secret(),
            'code': code,
            'grant_type': 'authorization_code',
        }),
        {
            'Content-Type': 'application/x-www-form-urlencoded',
        }
    )
    http_resp = http_conn.getresponse()
    if http_resp.status == http.HTTPStatus.OK.value:
        tokens_obj = json.loads(http_resp.read().decode('utf-8'))
        logging.info('Tokens: %s' % tokens_obj)
        cf.set_refresh_token(tokens_obj['refresh_token'])
    else:
        logging.error('Unexpected response: %s %s\n%s' % (
            http_resp.status,
            http_resp.reason,
            http_resp.read().decode('utf-8', errors='replace')
        ))


if __name__ == '__main__':
    exit(main())