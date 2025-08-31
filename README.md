# Beez — WebSocket Runnable Demo (Aligned to Original Structure)

This is a **full project** bundle. Unzip directly into your `Beez` project root.

## Quickstart
```bash
# from ~/Python/Beez
unzip -o Beez_full_project.zip -d .

python -m venv .venv
source .venv/bin/activate

pip install -U pip
pip install -e ".[dev]"

python -m uvicorn bee_sim.main:app --reload --port 8000
# open http://localhost:8000
# open http://localhost:8000/metrics

```
