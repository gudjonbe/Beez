from __future__ import annotations
import pathlib, time, json
from typing import Optional

def ensure_run_dir(root: str = "runs", run_id: Optional[str] = None) -> pathlib.Path:
    p = pathlib.Path(root)
    p.mkdir(parents=True, exist_ok=True)
    if run_id is None:
        run_id = time.strftime("%Y%m%d-%H%M%S")
    d = p / run_id
    d.mkdir(parents=True, exist_ok=True)
    (d / "meta.json").write_text(json.dumps({"run_id": run_id, "created": time.time()}, indent=2))
    return d
