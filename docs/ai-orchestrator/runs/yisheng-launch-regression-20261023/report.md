<!-- ai-orchestrator:checkpoint:v1:yisheng-launch-regression-20261023 -->
# Task report: yisheng-launch-regression-20261023

- Repository: `A942199/paratee-livecaption`
- Proposed branch: `agent/yisheng-launch-regression-20261023`
- Code HEAD before memory writes: `7aaddad63b0cab118b0924aaffe969aad9710b3a`
- Outcome: `AWAITING_REVIEW`

## Observed task summary
Fixed confirmed Windows double-click startup regression (pip exited 106 despite working project .venv). Added regression test demonstrating failure on old code and passing after fix. Applied only yisheng_startup.py change to local project after exact backup verification. Windows local: 12 tests pass, bundle check 20 modules/12 assets, Parakeet/VAD selftest, pip check pass. Actual GUI screenshot succeeds from project .venv and separate base Python parent using automatic subprocess delegation. GitHub Windows CI passed on code commit; Codex independent review requested but not yet confirmed. PR draft not merged; no live audio/GPU test.

## Durable knowledge
Bootstrap must prefer a verified already-working project .venv before provisioning a second environment. Previous unit/selftest/bundle checks bypassed the actual startup path, allowing a regression. Preserve local backup work/backups/launch-regression-20261023/yisheng_startup.py, and verify external Python -> pythonw child real GUI before release.

## Evidence links
- https://github.com/A942199/paratee-livecaption/issues/4
- https://github.com/A942199/paratee-livecaption/pull/5
- https://github.com/A942199/paratee-livecaption/actions/runs/39912767051
- https://github.com/A942199/paratee-livecaption/commit/7aaddad63b0cab118b0924aaffe969aad9710b3a

## Release guard
Do not merge on this document alone; review and CI are not independently verified by memory.

