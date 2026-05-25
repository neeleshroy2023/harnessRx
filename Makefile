.PHONY: install eval eval-quick api ui test fmt baseline

export PYTHONPATH := backend

install:
	uv sync --all-extras

eval:
	uv run python -m app.runner.runner --features all

eval-quick:
	uv run python -m app.runner.runner --features classify --no-judge

api:
	uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

ui:
	cd frontend && npm install && npm run dev

test:
	uv run pytest -q

fmt:
	uv run ruff format .

baseline:
	uv run python -m app.runner.baseline baselines/main.json $(RUN)
