# Louisbot4
discord message statistics bot

Louis sits in the background and tallies messages, including emoji count on said message, every 50 (configurable) messages. louis can then be invoked by a discord command, to give instant statistic data.
</br>
This is the fourth iteration of LouisBot, and the first to use this passive tally system, older methods which did a bulk scan, from scatch, at every invokation, they also had no server integration, and could only be invoked via the command line, as the program was a one shot. louisbot4 is a great improvement in methodolgy.


## database
louisbot needs a directory assigned to it which will be its database, each server will create a directory in the database with the same name as the name of the serverid given in the config, which contains a json file of the database json file of that year.
## Running
running louisbot is simple because it is python, it is also incredibly infuriating because it is python. to alleviate this it is recommended to use a virtual environment so that it does not pollute your system install. louisbot is built against python3.13 earlier versions might not work.
</br>
louisbot now uses [UV](https://docs.astral.sh/uv/) (a project management program inspired by cargo for python) it is not necessary to have uv installed to setup and run. (but makes it easier as it manages the python version itself too).

### Without UV

```bash
    git clone https://github.com/Nimrodium/louisbot4
    cd louisbot4
    python -m venv .venv
    ./.venv/bin/python -m pip install -r requirements.txt
    cd app
    ./.venv/bin/python main.py
```

### With UV

```bash
    git clone https://github.com/Nimrodium/louisbot4
    cd louisbot4
    cd app
    uv run main.py
```

## Config

on first run louisbot will prompt has an interactive setup to generate a config file at `./lb4_config.json` such as the one shown below:
```json
    {
    "batch_size": 50,
    "token": "yourtoken",
    "database": "./db",
    "prefix": "!",
    "dump_interval_minutes": 15,
    "tracked_servers": {
        "serverid": "friendserver",
        "serverid2": "schoolserver",
        }
    }
```

## As a SystemD service
Louisbot can be run on Linux and Windows, however i frankly have no idea how to make system services in windows, heres the .service file for systemd though
```s
[Unit]
  Description=Discord Server Statistics Bot
  After=network.target

[Service]
  WorkingDirectory=/path/to/louisbot4/app/
  ExecStart=/path/to/louisbot4/.venv/bin/python -u /path/to/louisbot4/app/main.py
  User=YourUser

  #StandardOutput=append:/path/to/louisbot4/logs/stdout.log
  #StandardError=append:/path/to/louisbot4/logs/stderr.log
[Install]
  WantedBy=multi-user.target
```

place this at `/etc/systemd/system/louisbot.service` and then:
```bash
    sudo systemctl daemon-reload
    sudo systemctl start louisbot
    sudo systemctl status louisbot
```
