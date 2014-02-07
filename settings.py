# -*- coding: utf-8 -*-

# Copyright © 2014 Puneeth Chaganti and others.
# See the LICENSE file for license rights and limitations (MIT).

import os

from os.path import abspath, dirname, exists, join


def read_heroku_env_file(name='.env'):
    env_path = join(dirname(abspath(__file__)), name)
    env = {}
    if exists(env_path):
        with open(env_path) as f:
            for line in f:
                key, value = line.split('=')
                env[key.strip()] = value.strip()
    return env


def get_config_var(name, default=''):
    value = os.environ.get(name, alternate_env.get(name, default))
    return value


alternate_env = read_heroku_env_file()
# Flask sample config
SQLALCHEMY_DATABASE_URI = get_config_var('DATABASE_URL', 'sqlite:///github.db')
SECRET_KEY = get_config_var('SECRET_KEY', 'top secret!')
CLIENT_ID = get_config_var('CLIENT_ID', 'x'*20)
CLIENT_SECRET = get_config_var('CLIENT_SECRET', 'y'*40)
STATE = get_config_var('STATE', '')
