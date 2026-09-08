"""sagar_attrib — M6: traffic gating, drift overlap scoring, the suspect model.

Read docs/SCORING_MODEL.md in full before changing anything here. It is
where the project both wins and is most capable of doing harm (its own
README's words, and true).

## What this package does NOT do

`f1_drift_consistency` (factors.py) needs `hit`/`coverage` from an M5
OpenDrift ensemble. This package does not run OpenDrift, does not import
it, and never will per its own scope — that stays in `sagar_drift`. Every
function here that needs a drift result takes it as an argument
(`DriftEvidence` in `model.py`). Building this module did not require
Docker, WSL2, or any external credentials; running the physics it
consumes still does.
"""
