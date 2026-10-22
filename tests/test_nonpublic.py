from pathlib import Path

from phillyschools.pde_nonpublic import _grade, _one_row, _sy, _two_row


def test_grade_labels():
    assert _grade("K 5") == "K5"
    assert _grade("K4") == "K4"
    assert _grade(7) == "07"
    assert _grade("7E") == "07"
    assert _grade("8S") == "08"
    assert _grade("12") == "12"
    assert _grade("EUG ") == "UG"
    assert _grade("Total Elementary Enrollment") is None
    assert _grade("Totals") is None


def test_school_year_from_file_name():
    assert _sy(Path("enrollment private nonpublic 2016-17.xlsx")) == 2017
    assert _sy(Path("enrollment private nonpublic 2025-2026.xlsx")) == 2026


def test_two_row_header_skips_residency_totals():
    rows = [
        ["title"],
        ["2022 - 2023"],
        [
            "AUN",
            "Institution",
            "IU",
            "County",
            "K5",
            None,
            9,
            None,
            "Total",
            "Total Non-Resident",
            None,
        ],
        [
            None,
            None,
            None,
            None,
            "Private Pay",
            "Fully Publicly Funded",
            "Private Pay",
            "Fully Publicly Funded",
            None,
            "Private Pay",
            "Fully Publicly Funded",
        ],
        [226510012, "A School", 26, "Philadelphia", 10, 0, 4, 1, 15, 3, 0],
    ]
    out = _two_row(rows, "all")
    assert [(r["grade"], r["funding"], r["count"]) for r in out] == [
        ("K5", "private_pay", 10.0),
        ("09", "private_pay", 4.0),
        ("09", "public_funded", 1.0),
    ]
    assert out[0]["aun"] == "226510012"


def test_one_row_header():
    rows = [
        ["title"],
        ["2025 - 2026"],
        [
            "AUNumber",
            "InstName",
            "InstCtgyCodes",
            "CountyName",
            "Private Pay - 9",
            "Public Funded - 9",
            "Totals",
        ],
        [226510012, "A School", "09", "Philadelphia", 25, 2, 27],
    ]
    out = _one_row(rows, "pa_resident")
    assert [(r["grade"], r["funding"], r["count"]) for r in out] == [
        ("09", "private_pay", 25.0),
        ("09", "public_funded", 2.0),
    ]
    assert out[0]["institution_category"] == "09"
    assert out[0]["residency"] == "pa_resident"
