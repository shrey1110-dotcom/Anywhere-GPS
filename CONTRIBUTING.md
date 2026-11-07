# Contributing

Use mock mode for development so tests do not touch a real phone:

```bash
.venv/bin/python -m pytest -q
./scripts/run.sh --mock
```

Build the frontend with `npm ci && npm run build` inside `frontend/`. Keep the
API bound to localhost, preserve explicit restore and loss handling, and never
silently reapply a location after a disconnect.

Do not include pairing records, account information, signed binaries,
provisioning profiles, protocol logs or real-location coordinates in commits
or issues. Run `scripts/verify_repository.py` against the staged index before
publishing. It checks common forbidden paths and credential patterns; manually
review anything the checker cannot establish.

Keep hardware observations evidence-based. Document device model/iOS and the
actual test method; mark untested behavior as untested. New device testing must
be on a phone you own or are authorized to test. Attendance/clock-in falsification
and geofence fraud are outside this project.

StikDebug is an independent upstream project. Read its pinned `AGENTS.md` before
working on or submitting its changes. It requires personal human review and
testing, human-written PR/issue descriptions, disclosed AI translation for those
descriptions, no AI attribution trailers and no AI localization translations.
This repository does not submit an upstream PR or claim that human source
review occurred. The recorded user phone tests are described in the test report.
