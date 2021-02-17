#!/bin/sh
set -e
ROOT=$PWD

if [ "$CI" != "true" ]; then
    echo "Creating venv"
    python -m venv venv
    echo "Activating venv"
    source venv/bin/activate
fi
echo "Installing deps for consumer"
cd $ROOT/consumer && pip install -r requirements.txt > /dev/null
echo "Installing deps for producer"
cd $ROOT/producer && pip install -r requirements.txt  > /dev/null
echo "Linting consumer"
cd $ROOT/consumer && flake8
echo "Linting producer"
cd $ROOT/producer && flake8
echo "Testing consumer"
cd $ROOT/consumer && pytest
echo "Testing producer"
cd $ROOT/producer && pytest