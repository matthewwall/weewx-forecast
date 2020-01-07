#!/usr/bin/env python
# Copyright: 2016-2020 Matthew Wall
# License: GPLv3

"""Tests for weewx forecast comparison generator."""

from __future__ import with_statement
import math
import os
import shutil
import string
import sys
import time
import unittest

import configobj

# if you try to run these tests on python 2.5 you might have to do a json
# import as it is done in forecast.py
import json

import weewx
import weewx.engine as engine

import forecast

# this is where to look for the unit test data files
TSTDIR = os.path.dirname(os.path.realpath(__file__))

# FIXME: these belong in a common testing library for weewx
TMPDIR = '/var/tmp/weewx_test'

def rmdir(d):
    try:
        os.rmdir(d)
    except:
        pass

def rmtree(d):
    try:
        shutil.rmtree(d)
    except:
        pass

def mkdir(d):
    try:
        os.makedirs(d)
    except:
        pass

def rmfile(name):
    try:
        os.remove(name)
    except:
        pass

def readfile(name, dir=TSTDIR):
    data = []
    fn = name if dir is None else dir + '/' + name
    with open(fn, 'r') as f:
        for line in f:
            data.append(line)
    return ''.join(data)
    
def get_tmpdir():
    return TMPDIR + '/test_forecast'

def get_testdir(name):
    return get_tmpdir() + '/' + name

# common methods to set up and tear down forecasting unit tests

def create_skin_config(test_dir, contents, skin_dir='testskin'):
    mkdir(test_dir + '/' + skin_dir)
    fn = test_dir + '/' + skin_dir + '/skin.conf'
    with open(fn, 'w') as f:
        f.write(contents)

def create_weewx_config(test_dir, service='', skin_dir='testskin'):
    cd = configobj.ConfigObj()
    cd['debug'] = 1
    cd['WEEWX_ROOT'] = test_dir
    cd['Station'] = {
        'station_type': 'Simulator',
        'altitude': [10,'foot'],
        'latitude': 42.358,
        'longitude': -71.106}
    cd['Simulator'] = {
        'driver': 'weewx.drivers.simulator',
        'mode': 'generator'}
    cd['Engine'] = {
        'Services': {
            'service_list' : service}}
    cd['DataBindings'] = {
        'wx_binding': {
            'database': 'wx_sqlite'},
        'forecast_binding': {
            'database': 'forecast_sqlite',
            'manager': 'weewx.manager.Manager',
            'schema': 'forecast.schema'}}
    cd['Databases'] = {
        'wx_sqlite': {
            'database_name': 'weewx.sdb',
            'database_type': 'SQLite'},
        'forecast_sqlite': {
            'database_name': 'forecast.sdb',
            'database_type': 'SQLite'}}
    cd['DatabaseTypes'] = {
        'SQLite': {
            'driver': 'weedb.sqlite',
            'SQLITE_ROOT': test_dir}}
    cd['StdReport'] = {
        'HTML_ROOT': test_dir + '/html',
        'SKIN_ROOT': test_dir,
        'fc': {
            'skin': skin_dir}}
    cd['StdArchive'] = {
        'data_binding': 'wx_binding'}
    cd['Forecast'] = {
        'data_binding': 'forecast_binding',
        'single_thread': True}
    return cd


class ForecastComparisonTest(unittest.TestCase):

    @staticmethod
    def _copy_database(tdir):
        shutil.copyfile('test/forecast.sdb', tdir+'/forecast.sdb')

    @staticmethod
    def _run_test(name, skin_contents):
        tdir = get_testdir(name)
        rmtree(tdir)
        create_skin_config(tdir, skin_contents)
        ForecastComparisonTest._copy_database(tdir)
        cd = create_weewx_config(tdir)
        si = weewx.station.StationInfo(**cd['Station'])
        ts = int(time.time())
        t = weewx.reportengine.StdReportEngine(cd, si, ts)
        t.run()

    def test_one_source_one_obs(self):
        self._run_test('test_one_source_one_obs', '''
[ForecastPlotGenerator]
    source = NWS
    [[plots]]
        [[[temp]]]
[Generators]
    generator_list = forecast.ForecastPlotGenerator
''')

    def test_one_source_multiple_obs(self):
        self._run_test('test_one_source_multiple_obs', '''
[ForecastPlotGenerator]
    source = NWS
    [[plots]]
        [[[temp]]]
        [[[humidity]]]
        [[[pop]]]
[Generators]
    generator_list = forecast.ForecastPlotGenerator
''')

    def test_multiple_source_one_obs(self):
        self._run_test('test_multiple_source_one_obs', '''
[ForecastPlotGenerator]
    source = NWS, WU, Aeris
    [[plots]]
        [[[temp]]]
[Generators]
    generator_list = forecast.ForecastPlotGenerator
''')

    def test_multiple_source_multiple_obs(self):
        self._run_test('test_multiple_source_multiple_obs', '''
[ForecastPlotGenerator]
    source = NWS, WU, Aeris
    [[plots]]
        [[[temp]]]
        [[[humidity]]]
        [[[pop]]]
[Generators]
    generator_list = forecast.ForecastPlotGenerator
''')

    def test_one_source_over_time(self):
        self._run_test('test_one_source_over_time', '''
[ForecastPlotGenerator]
    source = WU
    issued_since = 1454457600
    [[plots]]
        [[[temp]]]
[Generators]
    generator_list = forecast.ForecastPlotGenerator
''')

    def test_data_type(self):
        self._run_test('test_data_type', '''
[ForecastPlotGenerator]
    source = WU
    issued_since = 1454457600
    [[plots]]
        [[[the_temp]]]
            data_type = temp
[Generators]
    generator_list = forecast.ForecastPlotGenerator
''')

    def test_issued_offset(self):
        self._run_test('test_issued_offset', '''
[ForecastPlotGenerator]
    source = WU
    issued_since = -86400
    [[plots]]
        [[[temp]]]
[Generators]
    generator_list = forecast.ForecastPlotGenerator
''')

    def test_overlapping_columns(self):
        self._run_test('test_overlapping_columns', '''
[ForecastPlotGenerator]
    source = WU
    issued_since = -86400
    [[plots]]
        [[[temp_a]]]
            data_type = temp
        [[[temp_b]]]
            data_type = temp
[Generators]
    generator_list = forecast.ForecastPlotGenerator
''')


# PYTHONPATH=.:/home/weewx/bin python test/test_cmp.py
#
# use '--test test_name' to specify a single test

if __name__ == '__main__':

    # check for a single test, if not then run them all
    testname = None
    if len(sys.argv) == 3 and sys.argv[1] == '--test':
        testname = sys.argv[2]
    if testname is not None:
        unittest.TextTestRunner(verbosity=2).run(
            unittest.TestSuite(map(ForecastComparisonTest, [testname])))
    else:
        unittest.main()
