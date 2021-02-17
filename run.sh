#!/bin/sh
set -e
ROOT=$PWD
echo "Creating venv"
python -m venv venv
echo "Activating venv"
source venv/bin/activate

echo "Installing deps"
cd $ROOT/consumer && pip install -r requirements.txt > /dev/null
cd $ROOT/producer && pip install -r requirements.txt  > /dev/null
echo "Running"

trap "kill 0" EXIT

(cd $ROOT/consumer && python app.py) &
(cd $ROOT/producer && python app.py) &

wait