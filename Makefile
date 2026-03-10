u:
	uv run main.py

b:
	docker compose build

du:
	docker compose up -d && docker compose logs --tail 300 -f

dd:
	docker compose down

p:
	docker compose push

l:
	clear
	ruff format && ruff check --select I --fix ./src ./src/* ./tests/author/**
