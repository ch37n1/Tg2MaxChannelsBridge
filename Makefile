u:
	uv run main.py

db:
	docker compose build

du:
	docker compose up -d && docker compose logs --tail 300 -f

dd:
	docker compose down

l:
	clear
	ruff format && ruff check --select I --fix ./src ./src/* ./tests/author/**
