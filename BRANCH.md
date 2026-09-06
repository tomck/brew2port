# Branch `metamacpkg-db` (never merge to `main`)

This branch lets brew2port consume the
[metamacpkg](../README.md) mapping database instead of relying only on
local fuzzy matching.

## What changed vs `main`

- New module `brew2port/metamacpkg_db.py`: loads
  `mappings/brew-formula-to-macports.csv` and
  `mappings/brew-cask-to-macports.csv`, exposes `lookup()`.
- `brew2port/core.py`: `candidates()` and `make_plan()` accept an
  optional `catalog` (default `None`, so `main` behavior is unchanged
  when the flag is absent).
- `brew2port/cli.py`: `plan` and `prepare` accept
  `--catalog DIR` (the metamacpkg `mappings/` directory).
- New tests in `tests/test_metamacpkg_db.py`.

## Catalog semantics

| Catalog row | Effect |
|---|---|
| `confident`, target present locally | single candidate, reason `metamacpkg:<method>` |
| `confident`, target absent locally | ignored (stale snapshot), local matching runs |
| `missing` | **no candidates** — suppresses fuzzy lookalikes |
| `needs-review` / unknown | local matching runs as before |

## Usage

```sh
brew2port plan --inventory brew-inventory.json \
  --catalog ../mappings --output migration-plan.json
```

Point `--catalog` at a fresh `make build` output; the CSVs are a
snapshot and go stale as the three repositories evolve.
