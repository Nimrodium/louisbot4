#!/bin/bash
echo "beginning setup..."
SCRIPT_DIR="$(dirname "$(realpath "$0")")"
cd "$SCRIPT_DIR" || exit
EXE='./louisbot4.py'
INSTALL_DIR='./.venv/'
echo "creating virtual env"
/opt/python3.13/bin/python3.13 -m venv $INSTALL_DIR
source "$INSTALL_DIR/bin/activate"
if [ -z "$VIRTUAL_ENV" ];then
  echo "failed to make virtual python environment"
  exit
fi
pip install -r requirements.txt

echo "cd $SCRIPT_DIR||exit;source $INSTALL_DIR/bin/activate;python $EXE" > run.sh

service="[Unit]
Description=Discord Server Statistics Bot
After=network.target

[Service]
WorkingDirectory=${INSTALLDIR}
ExecStart=${INSTALLDIR}/.venv/bin/python -u ${INSTALLDIR}/louisbot4.py
User=$(whoami)

#StandardOutput=append:${INSTALLDIR}/logs/stdout.log
#StandardError=append:${INSTALLDIR}/logs/stderr.log
[Install]
WantedBy=multi-user.target
"


read -r -p "Install Service (systemd)? [y/N] " response
response=${response,,}    # tolower
if [[ "$response" =~ ^(yes|y)$ ]]
	path=/etc/systemd/system/louisbot.service
	echo "Writing \n${service}\n---\n to ${path}"
	echo ${service} | sudo tee ${path}
else
	echo "generated service file:\n---\n${service}\n"
fi

chmod +x run.sh
./run.sh
