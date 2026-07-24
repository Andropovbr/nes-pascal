PYTHON ?= python

.PHONY: test rom clean

test:
	$(PYTHON) -m unittest discover -s tests -v

rom:
	$(PYTHON) -m nes_pascal.cli examples/minimal.nsp -o build/minimal.nes

clean:
	$(PYTHON) -c "import shutil; shutil.rmtree('build', ignore_errors=True)"
