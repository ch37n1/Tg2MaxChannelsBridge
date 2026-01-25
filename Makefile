u:
	uv run main.py

l:
	clear
	ruff format && ruff check --select I --fix ./src ./src/* ./tests/author/**
