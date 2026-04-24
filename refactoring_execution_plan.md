# Django Backend Refactoring Execution Plan
## Examination Module - Branch: examination-v1-qwen

### Current State Analysis

**Files Present:**
- `services.py` (432 LOC) - ✅ Created
- `selectors.py` (326 LOC) - ✅ Created  
- `api/views.py` (3,789 LOC) - ⚠️ Needs cleanup
- `views.py` (1,953 LOC) - ⚠️ Needs refactoring

### Remaining Critical Tasks (by Severity)

#### CRITICAL Priority

**T-C1: Remove Duplicate Helper Functions from api/views.py**
- **Location**: api/views.py:L88-L304
- **Issue**: Duplicated Code (Exact Duplication) - Major
- **Functions to remove** (already in services.py):
  - `format_semester_display` (L88-L103)
  - `round_from_last_decimal` (L105-L120)
  - `calculate_spi_for_student` (L122-L153)
  - `trace_registration` (L155-L160)
  - `calculate_cpi_for_student` (L162-L240)
  - `parse_academic_year` (L242-L262)
  - `is_valid_grade` (L264-L278)
  - `gather_related_registrations` (L280-L302)
- **Action**: Delete these functions, imports already point to services.py

**T-C2: Fix Bare Except Clauses (Silent Exception Swallowing)**
- **Locations**: 
  - api/views.py:L1103 (GenerateTranscript.post)
  - api/views.py:L1439 (DownloadExcelAPI.post)
- **Issue**: Inconsistent Error Handling → Silent Exception Swallowing - Critical
- **Action**: Replace with specific exception handling + logging

**T-C3: Replace Direct ORM Queries with Selectors**
- **Issue**: Fat View → ORM Logic in View - Major
- **Locations**: 30+ instances in api/views.py
- **Action**: Replace with existing selector calls

#### MAJOR Priority

**T-M1: Remove Duplicate Constants**
- **Location**: api/views.py:L64-L84
- **Issue**: Duplicated Code - Major (GRADE_CONVERSION, ALLOWED_GRADES, PBI_AND_BTP_ALLOWED_GRADES)
- **Action**: Import from services.py, remove local definitions

**T-M2: Consolidate Validation Logic**
- **Issue**: Scattered Validation - Critical
- **Action**: Ensure all validation uses services.is_valid_grade()

### Execution Order

1. T-C1 (Remove duplicate functions)
2. T-M1 (Remove duplicate constants)
3. T-C2 (Fix bare except clauses)
4. T-C3 (Replace ORM queries with selectors)
5. T-M2 (Consolidate validation)

