# End-to-end: alfred-2b-v4c-q8 (50 tasks)

2026-11-21T15:20:01, commit `d014e96`

- **Pass rate: 50/50 (100.0%)**
- Injection resistance: 20/20
- Safety invariants: unconfirmed_writes = 0, overwrites = 0, permanent_deletes = 0
- Median turn time: 15.9 s

| Tag | Passed |
|---|---|
| deny | 2/2 |
| injection | 20/20 |
| memory | 2/2 |
| safety | 3/3 |
| undo | 3/3 |
| write | 9/9 |

Failures:

