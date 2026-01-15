DIST=$(CURDIR)/dist
SRC=$(CURDIR)/src
VENV=$(CURDIR)/.venv
BUILD=$(CURDIR)/.build

.PHONY: all prod dev clean update-variants-diagram

all: prod

$(VENV)/bin/activate:
	@echo "Setting up development virtual env in .venv"
	python -m venv .venv; \
	. .venv/bin/activate; \
	python -m pip install -r requirements.txt

update-variants-diagram:
	cd $(CURDIR)/.. && python make.py variants-diagram --update

$(DIST): $(VENV)/bin/activate
	. $(VENV)/bin/activate; \
	sphinx-build -a -n -E -b html $(SRC) $(DIST)
	# Clean unused files inherited from default theme
	rm -rf $(DIST)/.doctrees \
	    $(DIST)/.buildinfo \
	    $(DIST)/genindex.html \
	    $(DIST)/objects.inv \
	    $(DIST)/search.html \
	    $(DIST)/searchindex.js \
	    $(DIST)/_sources \
	    $(DIST)/_static/basic.css \
	    $(DIST)/_static/doctools.js \
	    $(DIST)/_static/documentation_options.js \
	    $(DIST)/_static/file.png \
	    $(DIST)/_static/jquery-3.5.1.js \
	    $(DIST)/_static/jquery.js \
	    $(DIST)/_static/language_data.js \
	    $(DIST)/_static/minus.png \
	    $(DIST)/_static/plus.png \
	    $(DIST)/_static/searchtools.js \
	    $(DIST)/_static/underscore-1.13.1.js

prod: $(DIST)

dev: $(VENV)/bin/activate
	. $(VENV)/bin/activate; \
	sphinx-autobuild -a $(SRC) $(DIST) --port=0 --open-browser

clean:
	rm -rf $(DIST) $(VENV) $(BUILD)
