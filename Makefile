VENV := .venv
PY := $(VENV)/bin/python

.PHONY: setup reproduce pdf all clean

setup:
	python3 -m venv $(VENV)
	$(PY) -m pip install --upgrade pip
	$(PY) -m pip install -r requirements.txt

reproduce:
	$(PY) scripts/reproduce_card_krueger.py

pdf:
	$(PY) scripts/export_pdf.py

all: reproduce pdf

clean:
	rm -rf $(VENV) data/processed.csv output/figure1_change_in_employment.png reproduction_report.md
