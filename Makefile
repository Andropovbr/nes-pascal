PYTHON ?= python

.PHONY: test test-all test-mesen benchmark rom clean validate

test:
	$(PYTHON) -m unittest discover -s tests -v

test-all: test

test-mesen:
	$(PYTHON) -m unittest tests.test_integration.MesenIntegrationTests -v

benchmark:
	$(PYTHON) tools/measure_benchmarks.py

rom:
	$(PYTHON) -m nes_pascal.cli examples/minimal.nsp -o build/minimal.nes

clean:
	$(PYTHON) -c "import shutil, glob, os; shutil.rmtree('build', ignore_errors=True); [os.remove(f) for f in glob.glob('*.log') + glob.glob('benchmark-report.md') if os.path.exists(f)]"

validate: test-all benchmark rom
