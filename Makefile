


all: test

test: .develop
	@py.test -q ./tests

isort:
	isort -rc odss
	isort -rc tests

flake: .flake

cov cover coverage:
	tox

install:
	@pip install -U pip
	@pip install -Ur requirements/dev.txt

.develop: .install-deps $(shell find odss -type f) .flake
	@pip install -e .
	@touch .develop

.install-deps: $(shell find requirements -type f)
	@pip install -U -r requirements/dev.txt
	@touch .install-deps

.flake: .install-deps $(shell find odss -type f) \
                      $(shell find tests -type f) 
	@flake8 odss tests
	@touch .flake

clean:
	@rm -rf `find . -name __pycache__`
	@rm -f `find . -type f -name '*.py[co]' `
	@rm -rf .cache
	@rm -f .coverage
	@rm -rf htmlcov
	@rm -rf cover
	@python setup.py clean
	@rm -rf .tox
	@rm -f .flake
	@rm -f .install-deps
	@rm -rf odss.egg-info

.PHONY: all flake test cov clean
