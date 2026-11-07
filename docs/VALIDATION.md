# Publication validation — November 7, 2026

| Check | Result |
| --- | --- |
| Existing backend mock-device suite | **40 passed**; one Starlette/httpx deprecation warning |
| Existing frontend production build | **Passed**, Vite 5.4.11; 35 modules transformed |
| Shell syntax for install, launch and patch application | **Passed** |
| Nineteen on-device patches against pinned source files | **Apply check passed** |
| Patched source equivalence to local candidate | **Passed**, with personal signing team deliberately omitted |
| Hardware observations | See [TEST_RESULTS.md](TEST_RESULTS.md); no new phone interaction during publication |

The patches were checked in an isolated temporary source tree. The original
dirty audit checkout and phone installation were not reset, rebuilt, re-signed,
or changed. Patch application does not establish a new binary's hardware result.

The publication process checks relative documentation links, validates the
compatibility observations, verifies patch hashes, and scans the complete Git
index for common credential patterns and forbidden artifacts. These checks are
limited safeguards, not a claim of exhaustive security review.

The final Git index is required to match the public working files. Private
handoffs remain ignored locally. Commit author addresses use a GitHub noreply
identity. The import history uses current timestamps and contains no empty or
backdated activity commits; see [HISTORY.md](HISTORY.md).
