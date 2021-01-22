SHELL = bash

CUR_DIR = $(CURDIR)

lint:
	source $(CURDIR)/.venv/bin/activate && \
	pylint script.tvmaze.scrobbler/libs \
	script.tvmaze.scrobbler/script.py \
	script.tvmaze.scrobbler/service.py

.PHONY = lint
