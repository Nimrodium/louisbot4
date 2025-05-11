#!/bin/bash
SCRIPT_DIR="$(dirname "$(realpath "$0")")"
cd "$SCRIPT_DIR" || exit
EXE='./louisbot4.py'
INSTALL_DIR='./.venv/'
python -m venv $INSTALL_DIR
source "$INSTALL_DIR/bin/activate"
if [ -z "$VIRTUAL_ENV" ];then
  echo "failed to make virtual python environment"
  exit
fi 
pip install -r requirements.txt

echo "cd $SCRIPT_DIR||exit;source $INSTALL_DIR/bin/activate;python $EXE" > run.sh
chmod +x run.sh
./run.sh
