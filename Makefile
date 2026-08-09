.PHONY: install test compile migrate run docker-build

install:
	python -m pip install -r requirements-dev.txt

compile:
	python -m compileall -q app main.py alembic

test: compile
	pytest -q

migrate:
	alembic upgrade head

run:
	uvicorn main:app --host 0.0.0.0 --port 8000 --reload

docker-build:
	docker build -t livetse-promotion-service:local .
