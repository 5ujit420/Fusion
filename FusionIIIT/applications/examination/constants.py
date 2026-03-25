"""
Examination module constants.

Centralises magic values previously scattered across views.
Fixes audit violations: V13, V30, V31.
"""

from decimal import Decimal

# ---------------------------------------------------------------------------
# Role constants (V30)
# ---------------------------------------------------------------------------
ROLE_ACADADMIN = "acadadmin"
ROLE_DEAN_ACADEMIC = "Dean Academic"
ROLE_ASSOCIATE_PROFESSOR = "Associate Professor"
ROLE_PROFESSOR = "Professor"
ROLE_ASSISTANT_PROFESSOR = "Assistant Professor"

PROFESSOR_ROLES = {
    ROLE_ASSOCIATE_PROFESSOR,
    ROLE_PROFESSOR,
    ROLE_ASSISTANT_PROFESSOR,
}

ADMIN_ROLES = {ROLE_ACADADMIN, ROLE_DEAN_ACADEMIC}
ALL_ALLOWED_ROLES = PROFESSOR_ROLES | ADMIN_ROLES

# ---------------------------------------------------------------------------
# Programme type constants (V31)
# ---------------------------------------------------------------------------
UG_PROGRAMMES = ["B.Tech", "B.Des"]
PG_PROGRAMMES = ["M.Tech", "M.Des", "PhD"]

# ---------------------------------------------------------------------------
# Grade conversion map (V13) — used for SPI/CPI calculation
# ---------------------------------------------------------------------------
grade_conversion = {
    "O": 1.0, "A+": 1.0, "A": 0.9, "B+": 0.8, "B": 0.7,
    "C+": 0.6, "C": 0.5, "D+": 0.4, "D": 0.3, "F": 0.2, "S": 0.0,
    **{f"A{i}": Decimal(str(0.9 + i * 0.01)) for i in range(1, 11)},
    **{f"B{i}": Decimal(str(0.8 + i * 0.01)) for i in range(1, 11)},
    **{
        f"{x/10:.1f}": Decimal(f"{x/100:.2f}")
        for x in range(20, 101)
    },
}

# ---------------------------------------------------------------------------
# Allowed grade sets (V13)
# ---------------------------------------------------------------------------
ALLOWED_GRADES = {
    "O", "A+", "A",
    "B+", "B",
    "C+", "C",
    "D+", "D", "F",
    "CD", "S", "X",
}

PBI_AND_BTP_ALLOWED_GRADES = {
    f"{x:.1f}" for x in [i / 10 for i in range(20, 101)]
}

# Courses that use PBI/BTP grade scale
PBI_BTP_COURSE_CODES = {"PR4001", "PR4002", "BTP4001"}

# All letter grades for distribution counting
ALL_GRADE_LETTERS = ["O", "A+", "A", "B+", "B", "C+", "C", "D+", "D", "F", "S", "X", "CD"]

# ---------------------------------------------------------------------------
# Upload constraints (V19)
# ---------------------------------------------------------------------------
MAX_CSV_FILE_SIZE = 5 * 1024 * 1024       # 5 MB
MAX_CSV_ROW_COUNT = 10_000

# ---------------------------------------------------------------------------
# Semester type ordering
# ---------------------------------------------------------------------------
SEMESTER_TYPE_ODD = "Odd Semester"
SEMESTER_TYPE_EVEN = "Even Semester"
SEMESTER_TYPE_SUMMER = "Summer Semester"
