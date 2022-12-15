# wallbox-charge-session-report
Tool to extract the charge-sessions from a Wallbox and generate reports per car/rfid-tag.

## Initialization
First, make sure to initialze a fresh virtual python environment by using the [initialize.sh](initialize.sh) shell script.

```bash
jgilla@Kerberos wallbox-charge-session-report % ./initialize.sh 
Dropping old environment...
Recreate new virtual environment...
Install requirements...
...
Initialization finished! Activate virtual environment via: source .venv/bin/activate
```

Once the virtual environment is prepared, join the shell into the environment.

```bash
jgilla@Kerberos wallbox-charge-session-report % source .venv/bin/activate
(.venv) jgilla@Kerberos wallbox-charge-session-report %
```

## Parameters
The following parameters can be used.

```bash
(.venv) jgilla@Kerberos wallbox-charge-session-report % python3 wallbox-charge-session-report.py
usage: wallbox-charge-session-report.py [-h] --config CONFIG [--startdate STARTDATE] [--enddate ENDDATE]
wallbox-charge-session-report.py: error: the following arguments are required: --config
```

## Output
The following output is generated on the CLI.

```bash
(.venv) jgilla@Kerberos wallbox-charge-session-report % python3 wallbox-charge-session-report.py --config config.yml --startdate 2022-10-01 --enddate 2022-11-30
Connection to Wallbox successful! Downloading report...
Download succeeded! Start parsing the data and filter per tag.

Search for sessions for tag: 04116b1aea6f85
> Found 1 accountable sessions.

Parsing finished. Display reports...

MZYV66E (04116b1aea6f85) – 01.10.2022 - 30.11.2022
14.11.2022      20:53:01        278.02kWh
Σ 27.8kWh x 0.41 €/kWh = 11.4€
```