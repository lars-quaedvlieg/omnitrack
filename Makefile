.PHONY: fix-style lint

fix-style:
	ruff format .
	ruff check . --fix

lint:
	ruff check .