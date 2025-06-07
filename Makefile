PYTHON=python3

exec_targets=\
	reroader.exe

all: exe

.PHONY: test
test:
	$(PYTHON) sort.py --base test

.PHONY: lint
lint: requirements
	-python3 -m mypy src/*.py
	-vulture src/*.py

requirements: requirements.txt
	${PYTHON} -m pip install -r requirements.txt
	touch requirements

clean:
	$(RM) -r __pycache__
	$(RM) -r build
	$(RM) -r dist/
	$(RM) -r litedist/

exe: requirements $(addprefix bin/,${exec_targets})

bin/reroader.exe: src/gui.py
	mkdir -p bin
	${PYTHON} -m PyInstaller \
		--paths src \
		--onefile \
		--console \
		--distpath bin \
		--workpath build \
		--specpath build \
		--name $(notdir $@) \
		$<

.PHONY: all clean exe doc mods