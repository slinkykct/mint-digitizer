@echo off
setlocal
python -m pip install --upgrade pip
python -m pip install .
python -m mazeint_digitizer.gui
