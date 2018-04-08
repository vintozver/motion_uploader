# -*- coding: utf-8 -*-

import configparser


class Config(object):
    def __init__(self):
        self._cf = configparser.ConfigParser()
        self._cf.read('motion_uploader.ini')
        self.camera_id = self._cf.get('camera', 'id')
        self.client_id = self._cf.get('app', 'client_id')
        self.client_secret = self._cf.get('app', 'client_secret')
        self.redirect_uri = self._cf.get('app', 'redirect_uri')

    def get_client_id(self):
        return self.client_id

    def get_client_secret(self):
        return self.client_secret

    def get_redirect_uri(self):
        return self.redirect_uri

    def get_camera_id(self):
        return self.camera_id

    @classmethod
    def get_refresh_token(cls):
        cf = configparser.ConfigParser()
        cf.read('motion_uploader.ini')
        return cf.get('refresh_token', 'value')

    @classmethod
    def set_refresh_token(cls, value):
        cf = configparser.ConfigParser()
        cf.read('motion_uploader.ini')
        try:
            cf.add_section('refresh_token')
        except configparser.DuplicateSectionError:
            pass
        cf.set('refresh_token', 'value', value)
        with open('motion_uploader.ini', 'w') as cf_file:
            cf.write(cf_file)
