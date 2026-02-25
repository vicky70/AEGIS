.PHONY: setup infra-up infra-down dev test seed clean

setup:
	python3 -m venv venv
	./venv/bin/pip3 install -r server/requirements.txt

infra-up:
	docker-compose up -d

infra-down:
	docker-compose down

dev:
	./aegisvenv/Scripts/uvicorn server.app.main:app --reload --host 127.0.0.1 --port 8000

test:
	./aegisvenv/Scripts/pytest server/tests -v --cov=server/app

seed:
	./aegisvenv/Scripts/python3 scripts/seed_database.py

clean:
	docker-compose down -v
	rm -rf venv __pycache__ .pytest_cache
