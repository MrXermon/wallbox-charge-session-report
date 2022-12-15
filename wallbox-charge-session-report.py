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

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.platypus import Table

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
def lookup_car(cars, sn):
    r_car = None
    for car in cars:
        if car['sn'] == sn:
            r_car = car
    return(r_car)


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

    # Add argument for output configuration.
    args_parser.add_argument(
        '--output',
        help='Options: cli, pdf',
        default='cli'
    )

    # Add argument to define start date.
    args_parser.add_argument(
        '--startdate',
        help='Start date to gather data (format: YYYY-MM-DD).',
        default=str(datetime.date.today().replace(day=1))
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

                # Fetch additional information from wallbox.
                r_manuf_serial_n = requests.get(
                    'http://' + config['wallbox']['ip'] + '/rest/manuf_serial_n',
                    headers={
                        'Authorization': session_id
                    }
                )
                if r_manuf_serial_n.status_code == 200 and r_manuf_serial_n.content:
                    manuf_serial_n = r_manuf_serial_n.content
                else:
                    manuf_serial_n = ''

                # Check if download succeded.
                if r_csv.status_code == 200 and r_csv.content:
                    charge_sessions = {}

                    # Debug output.
                    print('Download succeeded! Start parsing the data and filter per car.')
                    print()

                    # Iterate through cars and generate sum per car.
                    for car in config['cars']:
                        print('Search for sessions for car: ' + car['sn'])
                        l_charge_sessions = []

                        # Load and parse csv once per tag to include all rows.
                        csv_parsed = csv.reader(r_csv.content.decode('utf-8').splitlines(), delimiter=';')

                        # Iterate through CSV.
                        for row in csv_parsed:
                            # Check if row contains data from specific tag.
                            if row[5] == car['sn'] and datetime.datetime.strptime(row[1], '%d.%m.%Y') >= args.startdate and datetime.datetime.strptime(row[1], '%d.%m.%Y') <= args.enddate:
                                # Add session to list.
                                l_charge_sessions.append({
                                    'session_number': row[0],
                                    'start_date': row[1],
                                    'start_time': row[2],
                                    'duration': row[3],
                                    'energy': int(row[4])
                                })
                        # Add sessions to global list.
                        charge_sessions[car['sn']] = l_charge_sessions

                        print('> Found ' + str(len(l_charge_sessions)) + ' accountable sessions.')

                    # Debug output.
                    print()
                    print('Parsing finished. Generating reports...')
                    print()

                    if args.output == 'cli':
                        # Output on the CLI. Iterate through cars and generate report.
                        for sn in charge_sessions:
                            car = lookup_car(config['cars'], sn)
                            print(car['plate'] + ' (' + sn + ') – ' + args.startdate.strftime('%d.%m.%Y') + ' - ' + args.enddate.strftime('%d.%m.%Y'))

                            # Iterate though charging sessions.
                            energy_sum = 0
                            for session in charge_sessions[sn]:
                                energy_sum += session['energy']
                                print(session['start_date'] + "\t" + session['start_time'] + "\t" + str(round(session['energy'] / 1000, 2)) + 'kWh')

                            print('Σ ' + str(round(energy_sum / 1000, 2)) + 'kWh x ' + str(config['power']['cost']) + ' €/kWh = ' + str(round(energy_sum / 1000 * config['power']['cost'], 2)) + '€')
                            print()

                    elif args.output == 'pdf':
                        # Output as PDF.
                        print('Generate PDF per car and save it to ' + os.path.abspath(os.path.dirname( __file__ )) + '/export' + ' folder.')

                        # Iterate through cars and generate report.
                        for sn in charge_sessions:
                            car = lookup_car(config['cars'], sn)
                            
                            # Basic PDF setup.
                            pdf_path = os.path.abspath(os.path.dirname( __file__ )) + '/export/' + args.startdate.strftime('%Y-%m-%d') + '-' + args.enddate.strftime('%Y-%m-%d') + '_' + car['plate'] + '.pdf'
                            pdf_w, pdf_h = A4
                            pdf = canvas.Canvas(
                                pdf_path,
                                pagesize=A4
                            )
                            pdf.setTitle('Verbrauchsabrechnung Strombezug')
                            pdf.setFont('Helvetica', 10)

                            # Add debitor to PDF.
                            pdf_textblock = pdf.beginText(pdf_w * 0.1, pdf_h * 0.925)
                            for line in car['debitor'].split("\n"):
                                pdf_textblock.textLine(line)
                            pdf.drawText(pdf_textblock)

                            # Add headline and current date to PDF.
                            pdf.drawCentredString(pdf_w / 2, pdf_h * 0.8, 'Verbrauchsabrechnung Strombezug')
                            pdf.drawRightString(pdf_w * 0.9, pdf_h * 0.8, datetime.date.today().strftime('%d.%m.%Y'))

                            # Add timerange data to PDF.
                            pdf.drawString(pdf_w * 0.1, pdf_h * 0.77, 'Zeitraum:')
                            pdf.drawString(pdf_w * 0.3, pdf_h * 0.77, args.startdate.strftime('%d.%m.%Y') + ' - ' + args.enddate.strftime('%d.%m.%Y'))                     

                            # Add car data to PDF.
                            pdf_textblock = pdf.beginText(pdf_w * 0.1, pdf_h * 0.75)
                            pdf_textblock.textLine('Fahrzeug:')
                            pdf_textblock.textLine('Kennzeichen:')
                            pdf.drawText(pdf_textblock)
                            pdf_textblock = pdf.beginText(pdf_w * 0.3, pdf_h * 0.75)
                            pdf_textblock.textLine(car['type'])
                            pdf_textblock.textLine(car['plate'])
                            pdf.drawText(pdf_textblock)

                            # Add outlet data to PDF.
                            pdf_textblock = pdf.beginText(pdf_w * 0.1, pdf_h * 0.715)
                            pdf_textblock.textLine('Verbrauchsstelle:')
                            pdf_textblock.textLine('Nummer:')
                            pdf.drawText(pdf_textblock)
                            pdf_textblock = pdf.beginText(pdf_w * 0.3, pdf_h * 0.715)
                            pdf_textblock.textLine(config['power']['model'])
                            pdf_textblock.textLine(manuf_serial_n)
                            pdf.drawText(pdf_textblock)                            

                            # Add supplier data to PDF.
                            pdf_textblock = pdf.beginText(pdf_w * 0.1, pdf_h * 0.68)
                            pdf_textblock.textLine('Lieferrant:')
                            pdf_textblock.textLine('Tarif:')
                            pdf.drawText(pdf_textblock)
                            pdf_textblock = pdf.beginText(pdf_w * 0.3, pdf_h * 0.68)
                            pdf_textblock.textLine(config['power']['supplier'])
                            pdf_textblock.textLine(config['power']['tarif'])
                            pdf.drawText(pdf_textblock)

                            # Add text.
                            pdf_textblock = pdf.beginText(pdf_w * 0.1, pdf_h * 0.64)
                            pdf_textblock.textLine('Der Zeitraum der Zählererfassung ist der o.g. Zeitraum jeweils von 00:00 bis 23:59 Uhr.')
                            pdf_textblock.textLine('Ich bitte um Erstattung der Kosten im Rahmen des steuerfreien Auslagenersatzes.')
                            pdf.drawText(pdf_textblock)

                            # Add line.
                            pdf.line(pdf_w * 0.1, pdf_h * 0.595, pdf_w * 0.9, pdf_h * 0.595)

                            # Create table.
                            pdf_table_date = pdf.beginText(pdf_w * 0.1, pdf_h * 0.55)
                            pdf_table_date.textLine('Datum')
                            pdf_table_date.textLine('')
                            pdf_table_time = pdf.beginText(pdf_w * 0.2675, pdf_h * 0.55)
                            pdf_table_time.textLine('Zeit')
                            pdf_table_time.textLine('')
                            pdf_table_duration = pdf.beginText(pdf_w * 0.4, pdf_h * 0.55)
                            pdf_table_duration.textLine('Dauer')
                            pdf_table_duration.textLine('')
                            pdf_table_sn = pdf.beginText(pdf_w * 0.51, pdf_h * 0.55)
                            pdf_table_sn.textLine('S/N')
                            pdf_table_sn.textLine('')
                            pdf_table_usage = pdf.beginText(pdf_w * 0.675, pdf_h * 0.55)
                            pdf_table_usage.textLine('Verbrauch')
                            pdf_table_usage.textLine('')
                            pdf_table_costs = pdf.beginText(pdf_w * 0.825, pdf_h * 0.55)
                            pdf_table_costs.textLine('Kosten')
                            pdf_table_costs.textLine('')

                            # Iterate though charging sessions.
                            energy_sum = 0
                            for session in charge_sessions[sn]:
                                energy_sum += session['energy']
                                pdf_table_date.textLine(session['start_date'])
                                pdf_table_time.textLine(session['start_time'])
                                pdf_table_duration.textLine(session['duration'])
                                pdf_table_sn.textLine(car['sn'])
                                pdf_table_usage.textLine(str(round(session['energy'] / 1000, 2)) + ' kWh')
                                pdf_table_costs.textLine(str(round(session['energy'] / 1000 * config['power']['cost'], 2)) + ' €')

                            
                            # Add sum to the end.
                            pdf_table_usage.textLine('')
                            pdf_table_usage.textLine(str(round(energy_sum / 1000, 2)) + ' kWh')
                            pdf_table_costs.textLine('')
                            pdf_table_costs.textLine(str(round(energy_sum / 1000 * config['power']['cost'], 2)) + ' €')

                            # Render table.
                            pdf.drawText(pdf_table_date)
                            pdf.drawText(pdf_table_time)
                            pdf.drawText(pdf_table_duration)
                            pdf.drawText(pdf_table_sn)
                            pdf.drawText(pdf_table_usage)
                            pdf.drawText(pdf_table_costs)



                            # Render PDF
                            pdf.showPage()
                            pdf.save()
                    
                else:
                    quit('Charge report could not be downloaded.')
            else:
                quit('Connection to wallbox did not work!')

    else:
        quit('Configuration could not be loaded.')