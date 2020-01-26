#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Funkfeuer Housing Management

Copyright (C) 2017 Clemens Hopfer <datacop@wireloss.net>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import os, sys, platform

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

def file_list(path):
    files = []
    for filename in os.listdir(path):
        if os.path.isfile(path+'/'+filename):
            files.append(path+'/'+filename)
    return files

setup(
    name='funkfeuer-housing',
    version="1.0.8",
    description='Funkfeuer Housing Management and Billing',
    author='Clemens Hopfer',
    author_email='datacop@wireloss.net',
    url='https://github.com/oe1rfc/',
    license="GPL v3",
    packages=['ff_housing', 'ff_housing',
        'ff_housing.controller', 'ff_housing.model', 
        'ff_housing.view'],
    include_package_data=True,
    scripts=['bin/funkfeuer-housing'],
    install_requires=[
        "Flask",
        "Flask-Admin",
        "Flask-Login>=0.3.0,<0.4",
        "Flask-security",
        "flask-wtf",
        "wtforms",
        "flask_sqlalchemy",
        "Flask-Script",
        "Flask-Mail",
        "flask-migrate",
        "sqlalchemy",
        "sqlalchemy_schemadisplay",
        "psycopg2-binary",
        "ipaddress",
        "python-dateutil",
        "jinja2<2.9",
        "latex",
        "sepaxml",
        "python-stdnum",
        "requests"
        ]
)
