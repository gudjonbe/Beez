.PHONY: run dev lint test clean

run:
	python -m uvicorn bee_sim.main:app --reload --port 8000

dev:
	python -m venv .venv && . .venv/bin/activate && pip install -U pip && pip install -e ".[dev]"

lint:
	@echo "Add ruff/black/mypy here later."

test:
	pytest -q

clean:
	rm -rf .venv dist build *.egg-info
