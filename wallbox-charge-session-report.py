#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script to fetch and display a charge-session report per car.
"""

import argparse
import os
import yaml
import requests
import hashlib
import csv
import datetime

# Function to load and validate yml configuration.
def config_load(path):
    # Check if file exists.
    if os.path.exists(path):
        with open(path, 'r') as stream:
            # Try to decode yaml file.
            try:
                # Return configuration if valid.
                return(yaml.safe_load(stream))
            except yaml.YAMLError as exec:
                # Print execution if not valid.
                print(exec)
                return(False)
    else:
        # Files does not exist.
        return(False)

# Lookup plate from list of rfid tags.
def lookup_plate(tags, sn):
    plate = ''
    for tag in tags:
        if tag['sn'] == sn:
            plate = tag['plate']
    return(plate)


# Main function including the magic.
if __name__ == '__main__':
    # Initialize argparse.
    args_parser = argparse.ArgumentParser()

    # Add argument for configuration file.
    args_parser.add_argument(
        '--config',
        help='Path to configuration file.',
        required=True,
        type=argparse.FileType('r', encoding='UTF-8')
    )

    # Add argument to define start date.
    args_parser.add_argument(
        '--startdate',
        help='Start date to gather data (format: YYYY-MM-DD).',
        default=str(datetime.date.today())
    )

    # Add argument to define end date.
    args_parser.add_argument(
        '--enddate',
        help='End date to gather data (format: YYYY-MM-DD).',
        default=str(datetime.date.today())
    )

    # Parse configuratiion variables from CLI.
    args = args_parser.parse_args()

    # Check if configuration is passed.
    if args.config.name and config_load(args.config.name):
        # Decode and load configuration.
        config = config_load(args.config.name)

        # Fix start- and enddate.
        args.startdate = datetime.datetime.strptime(args.startdate, '%Y-%m-%d')
        args.enddate = datetime.datetime.strptime(args.enddate, '%Y-%m-%d')

        # Try to fetch login token from wallbox.
        r_login_token = requests.get(
            'http://' + config['wallbox']['ip'] + '/json/login',
        )
        if r_login_token.status_code == 200 and 'token' in r_login_token.json():
            r_login_token = r_login_token.json()['token']

            # Try to login against wallbox.
            r_login = requests.post(
                'http://' + config['wallbox']['ip'] + '/json/login',
                json={
                    'username': config['wallbox']['user'],
                    'password': hashlib.sha256((config['wallbox']['password'] + r_login_token).encode('utf-8')).hexdigest()                    
                }
            )

            # Check if login was successful.
            if r_login.status_code == 200 and r_login.json()['logged_in']:
                print('Connection to Wallbox successful! Downloading report...')
                session_id = r_login.json()['session']['id']
                
                # Try to download CSV report from wallbox.
                r_csv = requests.get(
                    'http://' + config['wallbox']['ip'] + '/export/csv',
                    headers={
                        'Authorization': session_id
                    }
                )
                
                # Check if download succeded.
                if r_csv.status_code == 200 and r_csv.content:
                    charge_sessions = {}

                    # Debug output.
                    print('Download succeeded! Start parsing the data and filter per tag.')
                    print()

                    # Iterate through RFID tags and generate sum per tag.
                    for tag in config['rfid_tags']:
                        print('Search for sessions for tag: ' + tag['sn'])
                        l_charge_sessions = []

                        # Load and parse csv once per tag to include all rows.
                        csv_parsed = csv.reader(r_csv.content.decode('utf-8').splitlines(), delimiter=';')

                        # Iterate through CSV.
                        for row in csv_parsed:
                            # Check if row contains data from specific tag.
                            if row[5] == tag['sn'] and datetime.datetime.strptime(row[1], '%d.%m.%Y') >= args.startdate and datetime.datetime.strptime(row[1], '%d.%m.%Y') <= args.enddate:
                                # Add session to list.
                                l_charge_sessions.append({
                                    'session_number': row[0],
                                    'start_date': row[1],
                                    'start_time': row[2],
                                    'duration': row[3],
                                    'energy': int(row[4])
                                })
                        # Add sessions to global list.
                        charge_sessions[tag['sn']] = l_charge_sessions

                        print('> Found ' + str(len(l_charge_sessions)) + ' accountable sessions.')

                    # Debug output.
                    print()
                    print('Parsing finished. Display reports...')
                    print()

                    # Iterate through tags and generate report.
                    for sn in charge_sessions:
                        print(lookup_plate(config['rfid_tags'], sn) + ' (' + sn + ') – ' + args.startdate.strftime('%d.%m.%Y') + ' - ' + args.enddate.strftime('%d.%m.%Y'))

                        # Iterate though charging sessions.
                        energy_sum = 0
                        for session in charge_sessions[sn]:
                            energy_sum += session['energy']
                            print(session['start_date'] + "\t" + session['start_time'] + "\t" + str(round(session['energy'] / 100, 2)) + 'kWh')

                        print('Σ ' + str(round(energy_sum / 1000, 2)) + 'kWh x ' + str(config['app']['cost']) + ' €/kWh = ' + str(round(energy_sum / 1000 * config['app']['cost'], 2)) + '€')
                        print()
                    
                else:
                    quit('Charge report could not be downloaded.')
            else:
                quit('Connection to wallbox did not work!')

    else:
        quit('Configuration could not be loaded.')