# Project memory: YishengTranslator Windows Japanese live translation

- Repository: `A942199/paratee-livecaption`
- Source HEAD at initialization: `eabf7e261c2c5d8e82a401fff40ece96fc270bed`
- Initialized for run: `yisheng-auto-env-20261023`

## Verified project purpose
Personal-use Windows Python .pyw application that recognizes Japanese speech and translates subtitles. Implement optional first-run dependency provisioning on a separate review branch. Source is currently local only; remote main has only a README.

## Durable decisions and lessons
Add only verified project decisions and outcomes; do not include secrets.

<!-- ai-orchestrator:checkpoint:v1:yisheng-launch-regression-20261023 -->
## Durable checkpoint: yisheng-launch-regression-20261023
- Outcome: `AWAITING_REVIEW`
- Code HEAD before memory writes: `7aaddad63b0cab118b0924aaffe969aad9710b3a`
- Verified knowledge to retain: Bootstrap must prefer a verified already-working project .venv before provisioning a second environment. Previous unit/selftest/bundle checks bypassed the actual startup path, allowing a regression. Preserve local backup work/backups/launch-regression-20261023/yisheng_startup.py, and verify external Python -> pythonw child real GUI before release.
- Source task: `docs/ai-orchestrator/runs/yisheng-launch-regression-20261023/report.md`

