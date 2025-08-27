Beez Phase A – Roles + Signal Sensing

Apply from your project root (where `src/` lives):
    unzip -o Beez_phaseA_roles_patch_v2.zip -d .
    python -m uvicorn bee_sim.main:app --reload --port 8000

This patch adds:
- src/bee_sim/domain/agents/roles.py
- src/bee_sim/domain/agents/behaviors/communication.py
- updates src/bee_sim/domain/agents/bee.py
- updates src/bee_sim/domain/agents/worker.py

Assumes your World already owns a SignalBus (from the communication patch).
