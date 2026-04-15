PYTHON ?= python

.PHONY: install test eval-gate run docker-up docker-down

install:
	$(PYTHON) -m pip install -r requirements.txt

test:
	pytest -q tests

eval-gate:
	$(PYTHON) -m evaluation.eval_gate

run:
	uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload

docker-up:
	docker compose up -d --build

docker-down:
	docker compose down
