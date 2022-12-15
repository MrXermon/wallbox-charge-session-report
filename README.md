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