u:
	uv run main.py

c: coverage

coverage:
	.venv/bin/python -m pytest --cov=db --cov=handlers --cov=utils --cov-report=term-missing --cov-fail-under=$${COVERAGE_MIN:-90}

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
