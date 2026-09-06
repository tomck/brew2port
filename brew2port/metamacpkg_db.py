"""metamacpkg catalog backend (branch metamacpkg-db only).

Loads the confident one-to-one mappings built by metamacpkg
(mappings/brew-formula-to-macports.csv, mappings/brew-cask-to-macports.csv)
and consults them before brew2port's local heuristic matching.

Rules:
  * catalog row `confident` + target still present in the ports list
    -> that single candidate (reason "metamacpkg:<method>").
  * catalog row `confident` but target absent locally
    -> ignored (catalog stale); falls back to local matching.
  * catalog row `missing` -> no candidates at all. This is the point:
    git-svn must NOT fuzzy-match to gitsign, muse-code must NOT match
    mmencode, node must NOT match ode.
  * catalog row `needs-review` or no row -> existing local matching.
"""
import csv
from pathlib import Path

CONFIDENT_MIN = 0.9
# Local heuristic candidates below this are dropped when the catalog says
# needs-review: without evidence they are the R-sodium/gitsign class of
# wrong answers. Strong local tiers (exact/normalized/alias) always pass.
HEURISTIC_MIN_UNDER_REVIEW = 0.9
STRONG_REASONS = {"exact name", "normalized name", "alias/provides/replaces"}


def get_row(catalog, kind, name):
    return (catalog or {}).get(kind, {}).get(name)


def filter_review(cands):
    return [c for c in cands
            if c.get("reason") in STRONG_REASONS
            or c.get("confidence", 0) >= HEURISTIC_MIN_UNDER_REVIEW]


def catalog_paths(catalog_dir):
    d = Path(catalog_dir).expanduser()
    return {"formula": d / "brew-formula-to-macports.csv",
            "cask": d / "brew-cask-to-macports.csv"}


def load(catalog_dir):
    """Load both mapping CSVs; missing files yield empty tables."""
    tables = {}
    for kind, path in catalog_paths(catalog_dir).items():
        rows = {}
        if path.exists():
            with open(path, newline="") as f:
                for r in csv.DictReader(f):
                    rows[r["source"]] = r
        tables[kind] = rows
    return tables


def lookup(catalog, kind, name, port_names):
    """Return a brew2port-style candidate, [] for catalog-missing, or None
    to fall through to local matching."""
    row = (catalog or {}).get(kind, {}).get(name)
    if not row:
        return None
    if row.get("status") == "missing":
        return []
    if row.get("status") == "confident" and row.get("target"):
        try:
            if float(row.get("confidence") or 0) < CONFIDENT_MIN:
                return None
        except ValueError:
            return None
        if row["target"] not in port_names:
            return None  # stale catalog entry; do not trust blindly
        return [{"port": row["target"],
                 "confidence": float(row["confidence"]),
                 "reason": f"metamacpkg:{row.get('method', 'catalog')}"}]
    return None
