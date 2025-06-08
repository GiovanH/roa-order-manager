PYTHON=venv/Scripts/python.exe

exec_targets=\
	reroader.exe

.PHONY: all
all: lint test exe

.PHONY: lint
lint: venv
	-${PYTHON} -m mypy src/*.py
	-vulture src/*.py

.PHONY: test
test: venv
	${PYTHON} -m doctest src/*.py

venv: requirements.txt
	python3 -m venv ./venv
	${PYTHON} -m pip install -r requirements.txt
	${PYTHON} -m pip install pyinstaller

.PHONY: exe
exe: venv $(addprefix dist/,${exec_targets})

dist/reroader.exe: src/gui.py
	mkdir -p dist
	${PYTHON} -m PyInstaller \
		--paths src \
		--onefile \
		--console \
		--distpath dist \
		--workpath build \
		--specpath build \
		--name $(notdir $@) \
		$<

# Get GIT_TAG from environment variable, fallback to git command if not set
GIT_TAG ?= $(shell git describe --tags --abbrev=0 2>/dev/null || echo "v0.0.0-dev")

.PHONY: release
release: exe
	mv -v "dist/reroader.exe" "dist/reroader-$(GIT_TAG).exe"
