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
chmod +x run.sh
./run.sh
