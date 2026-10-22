"""PDE private and nonpublic school enrollment by institution, grade, funding, and residency.

The yearly workbooks use three layouts: 2016-17 to 2023-24 have one Elementary and one
Secondary sheet with a grade header row and a funding header row under it (grade totals only,
residency only as row totals); 2024-25 on split each level into PA-resident and non-resident
sheets with "Private Pay - 5" style headers. Grades 7 and 8 appear as 7E/8E (elementary
programs), 7S/8S (secondary programs, through 2019-20), or plain 7 and 8 (2024-25 on); all map
to grades 07 and 08, and `grade_label` keeps the source's label.
"""

import re

import pandas as pd
from python_calamine import CalamineWorkbook

from . import CORE, RAW

NONPUBLIC_DIR = RAW / "pde_nonpublic"
SOURCE = "pde_nonpublic"
FUNDING = {
    "private pay": "private_pay",
    "fully publicly funded": "public_funded",
    "public funded": "public_funded",
}


def _aun(value) -> str:
    return str(int(float(value))).zfill(9)


def _grade(label: str) -> str | None:
    s = re.sub(r"\s+", "", str(label)).upper()
    if s in {"K4", "K5"}:
        return s
    if s in {"EUG", "SUG"}:
        return "UG"
    m = re.fullmatch(r"(\d{1,2})(?:\.0)?[ES]?", s)
    return m.group(1).zfill(2) if m and 1 <= int(m.group(1)) <= 12 else None


def _sy(path) -> int:
    m = re.search(r"(\d{4})-(\d{2,4})", path.name)
    return int(m.group(1)) + 1


def _header_row(rows: list[list]) -> int:
    return next(i for i, r in enumerate(rows) if r and str(r[0]).strip() in {"AUN", "AUNumber"})


def _two_row(rows: list[list], residency: str) -> list[dict]:
    """2016-17 to 2023-24: grade labels on one row, funding labels on the next."""
    h = _header_row(rows)
    grades, funds = rows[h], rows[h + 1]
    cols, current = [], None
    for j, (g, f) in enumerate(zip(grades, funds, strict=False)):
        if g not in (None, ""):
            current = str(g).strip()
        fund = FUNDING.get(str(f).strip().lower()) if f else None
        if j >= 4 and fund and current and _grade(current):
            cols.append((j, current, fund))
    return _records(rows[h + 2 :], cols, residency, category_col=None)


def _one_row(rows: list[list], residency: str) -> list[dict]:
    """2024-25 on: "Private Pay - 5" style headers, one sheet per residency."""
    h = _header_row(rows)
    cols = []
    for j, c in enumerate(rows[h]):
        if " - " not in str(c):
            continue
        fund, label = (s.strip() for s in str(c).split(" - ", 1))
        if FUNDING.get(fund.lower()) and _grade(label):
            cols.append((j, label, FUNDING[fund.lower()]))
    return _records(rows[h + 1 :], cols, residency, category_col=2)


def _records(body, cols, residency, category_col) -> list[dict]:
    out = []
    for r in body:
        if not r or not str(r[0]).strip().replace(".0", "").isdigit():
            continue
        for j, label, fund in cols:
            v = r[j] if j < len(r) else None
            n = float(v) if isinstance(v, int | float) else None
            if not n:
                continue
            out.append(
                {
                    "aun": _aun(r[0]),
                    "institution_name": str(r[1]).strip(),
                    "county": str(r[3]).strip(),
                    "institution_category": str(r[category_col]).strip()
                    if category_col is not None and r[category_col] not in (None, "")
                    else None,
                    "grade": _grade(label),
                    "grade_label": label,
                    "funding": fund,
                    "residency": residency,
                    "count": n,
                }
            )
    return out


def read_year(path) -> pd.DataFrame:
    wb = CalamineWorkbook.from_path(str(path))
    recs = []
    for name in wb.sheet_names:
        level = next((lv for lv in ("Elementary", "Secondary") if name.startswith(lv)), None)
        if level is None:
            continue
        rows = wb.get_sheet_by_name(name).to_python()
        if "Resident" in name:
            residency = "non_pa_resident" if "Non" in name else "pa_resident"
            recs += _one_row(rows, residency)
        else:
            recs += _two_row(rows, "all")
    df = pd.DataFrame(recs)
    sy = _sy(path)
    df.insert(1, "sy", sy)
    df["status"] = "reported"
    df["source_id"] = f"{SOURCE}:sy{sy}"
    df["source_file"] = path.name
    return df


def build_nonpublic() -> pd.DataFrame:
    frames = [
        read_year(p) for p in sorted(NONPUBLIC_DIR.glob("enrollment private nonpublic *.xlsx"))
    ]
    df = pd.concat(frames, ignore_index=True)
    keys = ["aun", "sy", "grade", "grade_label", "funding", "residency"]
    dup = df.duplicated(keys, keep=False)
    if dup.any():
        raise ValueError(f"{int(dup.sum())} duplicate nonpublic enrollment rows")
    return df.sort_values(keys).reset_index(drop=True)


def write_nonpublic() -> pd.DataFrame:
    df = build_nonpublic()
    df.to_parquet(CORE / "nonpublic_enrollment.parquet", index=False)
    df.to_csv(CORE / "nonpublic_enrollment.csv", index=False)
    return df
