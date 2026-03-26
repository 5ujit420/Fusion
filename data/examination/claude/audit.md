# Examination Module — Structural Audit Report

---

## Section 1: Module Snapshot

| Metric                             | Value                   | How Measured                                                                                       |
| ---------------------------------- | ----------------------- | -------------------------------------------------------------------------------------------------- |
| Total LOC (approx.)                | 5,914                   | Sum of all `.py`files in the module                                                              |
| LOC in `views.py`                | 1,953                   | Line count of legacy views file                                                                    |
| LOC in `api/views.py`            | 3,764                   | Line count of API views file                                                                       |
| No. of service files               | 0                       | No `services.py`found                                                                            |
| No. of serializer classes          | 3                       | `CourseRegistrationSerializer`,`AnnouncementsSerializer`,`AuthenticationSerializer`          |
| No. of models                      | 4                       | `hidden_grades`,`authentication`,`grade`,`ResultAnnouncement`                              |
| Number of API endpoints            | 56 (33 API + 23 legacy) | Count from `urls.py`(23 active routes) +`api/urls.py`(33 routes)                               |
| Number of DB queries in views      | ~120+                   | Manual count of `.objects.`calls across both views files                                         |
| No. of structural violations       | 42                      | Counted in Section 2                                                                               |
| No. of redundancy items            | 12                      | Counted in Section 3                                                                               |
| `services.py`exists              | N                       | `ls`— file not found                                                                            |
| `selectors.py`exists             | N                       | `ls`— file not found                                                                            |
| `tests/`folder exists            | N                       | Only empty `tests.py`(3 lines:`from django.test import TestCase`)                              |
| `api/`folder exists              | Y                       | Contains `views.py`,`urls.py`,`serializers.py`                                               |
| Uses `TextChoices`               | N                       | Grade constants defined as raw set/dict literals at module level                                   |
| **Overall Structural State** | **Poor**          | No service/selector layer, massive fat views, no tests, duplicated logic across legacy & API views |

---

## Section 2: Structural Audit

### V01 — Missing Folder Structure

* **File:** Module root
* **Impact:** HIGH
* **Description:** `services.py` does not exist. All business logic (grade calculation, CSV parsing, PDF generation, role verification) lives directly in view functions.
* **Planned Fix:** Create `services.py` and extract all business logic from views.
* **Steps:**
  1. Create `services.py`.
  2. Move `calculate_spi_for_student`, `calculate_cpi_for_student`, `parse_academic_year`, `is_valid_grade`, `gather_related_registrations`, `trace_registration`, `round_from_last_decimal`, `format_semester_display`, `make_label`, grade upload logic, PDF generation logic into service functions.
  3. Update all views to call service functions.
  4. Verify by running tests and checking all endpoints return identical results.

---

### V02 — Missing Folder Structure

* **File:** Module root
* **Impact:** HIGH
* **Description:** `selectors.py` does not exist. Over 120 ORM queries are scattered across both views files.
* **Planned Fix:** Create `selectors.py` to encapsulate all `.objects.*` queries.
* **Steps:**
  1. Create `selectors.py`.
  2. Identify all distinct query patterns (e.g., `get_unverified_courses`, `get_student_grades_for_semester`, `get_course_registrations`).
  3. Extract each into a named selector function.
  4. Replace inline ORM calls in views with selector calls.
  5. Test each endpoint.

---

### V03 — Missing Tests ⚠️ CRITICAL

* **File:** `tests.py` (lines 1–3)
* **Impact:** CRITICAL
* **Description:** `tests.py` is empty (only boilerplate comment). No unit, integration, or API tests exist for any of the 56 endpoints.
* **Planned Fix:** Create `tests/` directory with comprehensive test suites.
* **Steps:**
  1. Create `tests/__init__.py`, `tests/test_models.py`, `tests/test_services.py`, `tests/test_selectors.py`, `tests/test_api.py`.
  2. Write tests for each service function, selector, and API endpoint.
  3. Cover edge cases: missing roles, invalid grades, nonexistent students, CSV malformation.

---

### V04 — Fat View

* **File:** `api/views.py` (lines 592–755)
* **Impact:** HIGH
* **Description:** `UploadGradesAPI.post()` is 163 lines: parses CSV, validates rows, checks registrations, performs `update_or_create` in transaction — all inline.
* **Planned Fix:** Extract CSV parsing, validation, and grade upsert into `services.upload_grades()`.
* **Steps:**
  1. Create `services.upload_grades(course_id, academic_year, semester_type, csv_data)`.
  2. Move validation logic, CSV parsing, row-level error collection, and `update_or_create` loop into the service.
  3. View becomes: parse request → call service → return response.
  4. Validate: upload a CSV and confirm identical response.

---

### V05 — Fat View

* **File:** `api/views.py` (lines 1703–1999)
* **Impact:** HIGH
* **Description:** `UploadGradesProfAPI.post()` is 296 lines: role check, programme type filtering, instructor ownership check, CSV parsing, atomic grade upsert.
* **Planned Fix:** Extract into `services.upload_grades_prof()`.
* **Steps:**
  1. Create service function handling instructor verification, programme filtering, CSV processing.
  2. View: extract request params → call service → respond.
  3. Validate: professor uploads CSV, check response.

---

### V06 — Fat View

* **File:** `api/views.py` (lines 1238–1493)
* **Impact:** HIGH
* **Description:** `GenerateResultAPI.post()` is 255 lines of Excel workbook generation inline (header styling, cell merging, SPI/CPI computation, row population).
* **Planned Fix:** Extract into `services.generate_result_excel()`.
* **Steps:**
  1. Create service that takes students, courses, semester params and returns `HttpResponse` with Excel.
  2. Move all `openpyxl` logic there.
  3. View becomes ~15 lines.
  4. Validate: download Excel, compare to current output.

---

### V07 — Fat View

* **File:** `api/views.py` (lines 2066–2468)
* **Impact:** HIGH
* **Description:** `GeneratePDFAPI.post()` is 402 lines: dispatches between faculty grade sheet and student result PDF, with full ReportLab PDF construction inline.
* **Planned Fix:** Split into two services: `services.generate_course_grade_pdf()` and `services.generate_student_result_pdf()`.
* **Steps:**
  1. Create two dedicated service functions.
  2. `GeneratePDFAPI.post()` becomes a thin dispatcher.
  3. Validate: generate both PDF types and confirm output matches.

---

### V08 — Fat View

* **File:** `api/views.py` (lines 3362–3677)
* **Impact:** HIGH
* **Description:** `GenerateStudentResultPDFAPI.post()` is 315 lines: duplicates nearly all logic from `GeneratePDFAPI.generate_student_result_pdf()` with minor differences (logo handling).
* **Planned Fix:** Consolidate into a single `services.generate_student_result_pdf()` used by both endpoints.
* **Steps:**
  1. Create single shared service function.
  2. Both API classes call the service.
  3. Validate: generate PDF from both endpoints, confirm identical layout.

---

### V09 — Fat View

* **File:** `views.py` (lines 918–1039)
* **Impact:** HIGH
* **Description:** `upload_grades()` is 121 lines of CSV parsing, grade upsert, and response generation — duplicates `UploadGradesAPI`.
* **Planned Fix:** Delete legacy view; use API version only.
* **Steps:**
  1. Ensure frontend uses API endpoint.
  2. Remove function and URL route.
  3. Validate: upload grades via API, verify success.

---

### V10 — Fat View

* **File:** `views.py` (lines 1527–1696)
* **Impact:** HIGH
* **Description:** `generate_pdf()` is 169 lines of ReportLab PDF generation — duplicates `GeneratePDFAPI`.
* **Planned Fix:** Delete legacy view; use API version only.

---

### V11 — Fat View

* **File:** `views.py` (lines 1700–1874)
* **Impact:** HIGH
* **Description:** `generate_result()` is 174 lines of Excel generation — duplicates `GenerateResultAPI`.
* **Planned Fix:** Delete legacy view; use API version only.

---

### V12 — No Service Layer Usage

* **File:** `api/views.py` (lines 97–128)
* **Impact:** HIGH
* **Description:** `calculate_spi_for_student()` and `calculate_cpi_for_student()` (lines 97–215) are module-level helper functions that should be in `services.py`. These contain core business logic (grade-point calculation, replacement tracking).
* **Planned Fix:** Move to `services.py`.
* **Steps:**
  1. Move both functions and their dependencies (`grade_conversion`, `trace_registration`, `round_from_last_decimal`) to `services.py`.
  2. Update imports in `api/views.py`.
  3. Validate: call transcript/result endpoints, confirm SPI/CPI values unchanged.

---

### V13 — No Service Layer Usage

* **File:** `api/views.py` (lines 39–61)
* **Impact:** MEDIUM
* **Description:** `grade_conversion`, `ALLOWED_GRADES`, `PBI_AND_BTP_ALLOWED_GRADES` are module-level constants embedded in views file.
* **Planned Fix:** Move to `services.py` or a dedicated `constants.py`.

---

### V14 — Security Issue ⚠️ CRITICAL

* **File:** `views.py` (line 371)
* **Impact:** CRITICAL
* **Description:** `Updatehidden_gradesMultipleView` uses `permission_classes = [AllowAny]` — allows unauthenticated users to modify grades.
* **Planned Fix:** Change to `[IsAuthenticated]` with role validation.
* **Steps:**
  1. Replace `AllowAny` with `IsAuthenticated`.
  2. Add role check inside `post()`.
  3. Validate: attempt unauthenticated request, confirm 401.

---

### V15 — Security Issue ⚠️ CRITICAL

* **File:** `views.py` (line 412)
* **Impact:** CRITICAL
* **Description:** `Submithidden_gradesMultipleView` uses `permission_classes = [AllowAny]`.
* **Planned Fix:** Change to `[IsAuthenticated]` with role validation. (Same as V14.)

---

### V16 — Security Issue ⚠️ CRITICAL

* **File:** `views.py` (line 681)
* **Impact:** CRITICAL
* **Description:** `moderate_student_grades` (legacy) uses `permission_classes = [AllowAny]`. Allows unauthenticated grade moderation.
* **Planned Fix:** Change to `[IsAuthenticated]`.
* **Steps:**
  1. Replace permission.
  2. Add proper DRF role check.
  3. Validate: unauthenticated POST returns 401.

---

### V17 — Security Issue ⚠️ CRITICAL

* **File:** `views.py` (line 807)
* **Impact:** CRITICAL
* **Description:** `submitEntergradesStoring` uses `permission_classes = [AllowAny]`.
* **Planned Fix:** Change to `[IsAuthenticated]`. (Same as V14.)

---

### V18 — Security Issue ⚠️ CRITICAL

* **File:** All views (throughout)
* **Impact:** CRITICAL
* **Description:** Role authorization is done by checking `request.data.get("Role")` — a client-supplied value. Attackers can send `"Role": "acadadmin"` and bypass all authorization.
* **Planned Fix:** Implement server-side role resolution via `HoldsDesignation` model lookup. Create a custom DRF permission class.
* **Steps:**
  1. Create `permissions.py` with `IsAcadAdmin`, `IsDeanAcademic`, `IsProfessor` classes.
  2. Each checks `HoldsDesignation` for the authenticated user.
  3. Replace all `request.data.get("Role")` checks.
  4. Validate: send request with fake role, confirm 403.

---

### V19 — Missing Input Validation

* **File:** `api/views.py` (lines 592–755)
* **Impact:** MEDIUM
* **Description:** `UploadGradesAPI` does not validate CSV content size limits. A malicious upload of millions of rows would cause OOM or timeout.
* **Planned Fix:** Add file size and row count limits.
* **Steps:**
  1. Check `csv_file.size` against a configurable max (e.g., 5MB).
  2. Count rows during iteration, abort if > threshold.
  3. Validate: upload oversized CSV, confirm rejection.

---

### V20 — Missing Input Validation

* **File:** `api/views.py` (lines 1060–1064)
* **Impact:** MEDIUM
* **Description:** `GenerateTranscript.post()` calls `json.loads(semester)` without try/except on the JSON parse. Malformed semester field causes unhandled 500.
* **Planned Fix:** Wrap in try/except and return 400.

---

### V21 — Missing Error Handling

* **File:** `api/views.py` (line 1078)
* **Impact:** MEDIUM
* **Description:** `GenerateTranscript.post()` has bare `except:` on line 1078, catching all exceptions silently — hides bugs.
* **Planned Fix:** Use specific exception types.
* **Steps:**
  1. Replace `except:` with `except Student.DoesNotExist:`.
  2. Add a second `except Exception as e:` with logging.
  3. Validate: request with invalid student ID returns proper error.

---

### V22 — Improper Exception Handling

* **File:** `api/views.py` (line 1414)
* **Impact:** LOW
* **Description:** `GenerateResultAPI.post()` has bare `except:` on line 1414, swallowing all errors when fetching user name.
* **Planned Fix:** Use `except User.DoesNotExist:`.

---

### V23 — Non-Standard Serializer Pattern

* **File:** `api/serializers.py` (lines 19–22)
* **Impact:** HIGH
* **Description:** `AuthenticationSerializer` uses `model = Announcements` instead of `model = authentication`. This is a bug — the serializer references the wrong model.
* **Planned Fix:** Fix the model reference to `authentication`.
* **Steps:**
  1. Change `model = Announcements` to `model = authentication` and import it.
  2. Validate: check if serializer is used anywhere; if not, document or remove.

---

### V24 — Non-Standard Serializer Pattern

* **File:** `api/serializers.py` (lines 1–22)
* **Impact:** HIGH
* **Description:** All 3 serializers exist but are never used in any view. API views manually construct Response dicts everywhere.
* **Planned Fix:** Use serializers for all API input validation and output formatting.
* **Steps:**
  1. Create proper serializers for each endpoint's input/output.
  2. Use `serializer.is_valid()` for input validation.
  3. Use `serializer.data` for response formatting.
  4. Validate: all endpoints return same structured data.

---

### V25–V28 — Dead Code (LOW)

| ID  | File         | Lines | Description                                                                                               |
| --- | ------------ | ----- | --------------------------------------------------------------------------------------------------------- |
| V25 | `views.py` | 408   | Unreachable `return render(...)`after `return response`in `Updatehidden_gradesMultipleView.post()`. |
| V26 | `views.py` | 727   | Unreachable `return render(...)`after `return response`in `moderate_student_grades.post()`.         |
| V27 | `views.py` | 782   | Unreachable `return HttpResponse(...)`after `return render(...)`in `submitEntergrades()`.           |
| V28 | `views.py` | 915   | Unreachable `return render(...)`in `submitEntergradesStoring.post()`.                                 |

**Fix:** Delete each unreachable line.

---

### V29 — Dead Code ⚠️ CRITICAL

* **File:** `views.py` (line 816)
* **Impact:** CRITICAL
* **Description:** `submitEntergradesStoring.post()` shadows the imported `Student_grades` model with a loop variable `Student_grades = request.POST.getlist("Student_grades[]")` on line 816. This makes the model inaccessible and causes `AttributeError` at line 852.
* **Planned Fix:** Rename the loop variable to `student_grades_list`.
* **Steps:**
  1. Rename variable on line 816 and corresponding `zip` usages.
  2. Validate: the endpoint can actually function.

---

### V30 — Hard-coded Values

* **File:** All views (throughout)
* **Impact:** MEDIUM
* **Description:** Role strings `"acadadmin"`, `"Dean Academic"`, `"Associate Professor"`, `"Professor"`, `"Assistant Professor"` are hardcoded in 40+ locations across both view files.
* **Planned Fix:** Define role constants in `constants.py` and reference them everywhere.
* **Steps:**
  1. Create `constants.py` with `ROLE_ACADADMIN = "acadadmin"`, etc.
  2. Replace all string literals.
  3. Validate: grep confirms no remaining raw role strings in views.

---

### V31 — Hard-coded Values

* **File:** `api/views.py` (lines 325–330, 396–398, 508–510, 1652–1654, 1777–1778, 2040–2042, 2976–2978)
* **Impact:** MEDIUM
* **Description:** Programme type mapping `['B.Tech', 'B.Des']` for UG and `['M.Tech', 'M.Des', 'PhD']` for PG is hardcoded in 7+ locations.
* **Planned Fix:** Define as constants: `UG_PROGRAMMES`, `PG_PROGRAMMES`.

---

### V32 — Performance Issue

* **File:** `api/views.py` (lines 1407–1416)
* **Impact:** MEDIUM
* **Description:** Inside `GenerateResultAPI.post()` student loop, `User.objects.get()` runs once per student — N+1 query.
* **Planned Fix:** Prefetch all user records in a single query before the loop.
* **Steps:**
  1. Fetch `User.objects.filter(username__in=student_ids)` before loop.
  2. Build a `{username: user}` map.
  3. Look up from map inside loop.

---

### V33 — Performance Issue

* **File:** `api/views.py` (lines 1435–1452)
* **Impact:** HIGH
* **Description:** Inside `GenerateResultAPI.post()`, for each student-course pair, `course_registration.objects.filter(...)` and `Student_grades.objects.filter(...)` are called inside a nested loop — O(students × courses) queries.
* **Planned Fix:** Prefetch all registrations and grades before the loop; build lookup dicts.

---

### V34 — Performance Issue

* **File:** `api/views.py` (lines 255–274)
* **Impact:** MEDIUM
* **Description:** `gather_related_registrations()` performs BFS with individual `course_replacement.objects.filter()` calls per node — unbounded N+1 for students with many replacements.
* **Planned Fix:** Prefetch all replacements for the student in one query, then traverse in memory.

---

### V35 — Inconsistent Naming

* **File:** `models.py` (lines 9–49)
* **Impact:** MEDIUM
* **Description:** Model names use `snake_case` (`hidden_grades`, `authentication`, `grade`) instead of Django convention `PascalCase`.
* **Planned Fix:** Rename to `HiddenGrade`, `Authentication`, `Grade` with `db_table` meta to avoid migration issues.
* **Steps:**
  1. Add `class Meta: db_table = 'examination_hidden_grades'` etc.
  2. Rename classes.
  3. Update all references.
  4. Validate: `makemigrations` shows no schema changes.

---

### V36 — Inconsistent Naming

* **File:** `api/urls.py` (lines 1–40)
* **Impact:** LOW
* **Description:** URL patterns mix camelCase (`submitGrades/`), snake_case (`upload_grades/`), and kebab-case (`result-announcements/`).
* **Planned Fix:** Standardize all URLs to kebab-case per REST convention.

---

### V37 — Cross-Module Tight Coupling

* **File:** `api/views.py` (lines 8–12, 28)
* **Impact:** MEDIUM
* **Description:** Direct imports from 5 external modules: `academic_procedures`, `programme_curriculum`, `academic_information`, `online_cms`, `department`.
* **Planned Fix:** Access cross-module data through selector functions rather than direct model imports where possible.

---

### V38 — Mixed Responsibilities

* **File:** `api/views.py` (lines 2066–2078)
* **Impact:** MEDIUM
* **Description:** `GeneratePDFAPI.post()` dispatches between faculty grade sheet and student result PDF based on request content — single endpoint serving two unrelated functions.
* **Planned Fix:** Split into two distinct endpoints.

---

### V39 — Missing Input Validation

* **File:** `api/views.py` (lines 3679–3764)
* **Impact:** MEDIUM
* **Description:** `GradeSummaryAPI` executes raw SQL with `cursor.execute(query, [academic_year, semester_type])`. While parameterized, raw SQL bypasses Django ORM protections and is harder to maintain.
* **Planned Fix:** Replace with ORM aggregation queries using `annotate()` and `Count()` with `Case/When`.

---

### V40 — Other

* **File:** `urls.py` (lines 2, 11)
* **Impact:** LOW
* **Description:** Uses deprecated `django.conf.urls.url()` throughout both URL files.
* **Planned Fix:** Replace with `django.urls.path()` / `re_path()`.

---

### V41 — Other

* **File:** `views.py` (lines 172, 248, 258, 671, 725, 1096, 1148, 1389)
* **Impact:** LOW
* **Description:** Multiple `print()` statements in production code (debugging leftovers).
* **Planned Fix:** Remove all `print()` calls; use `logging` module if needed.

---

### V42 — Other

* **File:** `views.py` (lines 621, 654, 688)
* **Impact:** MEDIUM
* **Description:** Uses `request.is_ajax()` which was removed in Django 4.0.
* **Planned Fix:** Check `request.headers.get('X-Requested-With') == 'XMLHttpRequest'` or use content-type check.

---

## Section 3: Redundancy Register

| ID  | Type       | Location 1                                                                   | Location 2                                                         | Redundant                           | Plan                                                  |
| --- | ---------- | ---------------------------------------------------------------------------- | ------------------------------------------------------------------ | ----------------------------------- | ----------------------------------------------------- |
| R01 | Code       | `views.py:918–1039` `upload_grades()`                                   | `api/views.py:592–755` `UploadGradesAPI`                      | Legacy view                         | Remove legacy; API is source of truth                 |
| R02 | Code       | `views.py:1211–1332` `upload_grades_prof()`                             | `api/views.py:1703–1999` `UploadGradesProfAPI`                | Legacy view                         | Remove legacy                                         |
| R03 | Code       | `views.py:680–727` `moderate_student_grades`                            | `api/views.py:953–1023` `ModerateStudentGradesAPI`            | Legacy view                         | Remove legacy                                         |
| R04 | Code       | `views.py:1527–1696` `generate_pdf()`                                   | `api/views.py:2066–2287` `GeneratePDFAPI`                     | Legacy view                         | Remove legacy                                         |
| R05 | Code       | `views.py:1700–1874` `generate_result()`                                | `api/views.py:1238–1493` `GenerateResultAPI`                  | Legacy view                         | Remove legacy                                         |
| R06 | Code       | `api/views.py:2293–2468` `GeneratePDFAPI.generate_student_result_pdf()` | `api/views.py:3362–3677` `GenerateStudentResultPDFAPI.post()` | `GeneratePDFAPI`internal method   | Merge into `GenerateStudentResultPDFAPI`            |
| R07 | Code       | `views.py:370–408` `Updatehidden_gradesMultipleView`                    | `views.py:411–439` `Submithidden_gradesMultipleView`          | `Submithidden_gradesMultipleView` | Consolidate into single view/service                  |
| R08 | Code       | `views.py:1822–1849`manual grade-to-credit calc                           | `views.py:1907–1933`same calc                                   | Both if/elif chains                 | Use `grade_conversion`dict from `api/views.py`    |
| R09 | Validation | `api/views.py:325–330`                                                    | 6 other locations                                                  | All but one                         | Create `selectors.get_students_by_programme_type()` |
| R10 | Query      | `views.py:616–646` `updateGrades()`                                     | `api/views.py:781–830` `UpdateGradesAPI`                      | Legacy view                         | Remove legacy                                         |
| R11 | Query      | `views.py:1152–1183` `verifyGradesDean()`                               | `views.py:1335–1364` `validateDean()`                         | One is redundant                    | Create `selectors.get_verified_courses()`           |
| R12 | Code       | `views.py:482–500` `DownloadExcelView`                                  | `api/views.py:1543–1596` `DownloadExcelAPI`                   | Legacy view                         | Remove legacy                                         |

---

## Section 4: Refactoring Plan

### Step 1 — Create Service and Constants Layer (V01, V12, V13)

* **Target Files:** New: `services.py`, `constants.py`. Modified: `api/views.py`.
* **Action:** Create `services.py` with all business logic: SPI/CPI calculation, grade validation, CSV processing, PDF generation, Excel generation. Move `grade_conversion`, `ALLOWED_GRADES`, `PBI_AND_BTP_ALLOWED_GRADES` and all helper functions from `api/views.py`.
* **Validation:** Unit test each service function. Confirm all API endpoints return identical responses before/after.

### Step 2 — Create Selector Layer (V02, R09, R10, R11)

* **Target Files:** New: `selectors.py`. Modified: `api/views.py`, `views.py`.
* **Action:** Create `selectors.py` with all reusable query functions: `get_unverified_courses()`, `get_verified_courses()`, `get_student_grades_for_semester()`, `get_students_by_programme_type()`, `get_course_registrations()`, etc.
* **Validation:** Each selector returns same queryset as the inline query it replaces.

### Step 3 — Create Test Suite (V03)

* **Target Files:** New: `tests/__init__.py`, `tests/test_models.py`, `tests/test_services.py`, `tests/test_selectors.py`, `tests/test_api.py`. Delete: `tests.py`.
* **Action:** Write comprehensive tests covering all endpoints and edge cases.
* **Validation:** `python manage.py test examination` passes. Coverage > 80%.

### Step 4 — Extract CSV Upload Logic (V04, V05, R01, R02)

* **Target Files:** Modified: `api/views.py`, `services.py`. Deleted from: `views.py`.
* **Action:** Extract CSV upload logic into `services.upload_grades()` and `services.upload_grades_prof()`. Thin out `UploadGradesAPI` and `UploadGradesProfAPI`. Delete legacy views.
* **Validation:** Upload CSV via API; confirm grades are saved correctly. Confirm legacy URL returns 404.

### Step 5 — Extract Excel Generation (V06, V11, R05, R08)

* **Target Files:** Modified: `api/views.py`, `services.py`. Deleted from: `views.py`.
* **Action:** Extract Excel generation into `services.generate_result_excel()`. Delete legacy `generate_result()`. Replace inline if/elif grade calculation with `grade_conversion` dict.
* **Validation:** Download Excel via API. Confirm format, SPI/CPI values match.

### Step 6 — Consolidate PDF Generation (V07, V08, V10, R04, R06)

* **Target Files:** Modified: `api/views.py`, `services.py`. Deleted from: `views.py`.
* **Action:** Consolidate all PDF generation into `services.generate_course_grade_pdf()` and `services.generate_student_result_pdf()`. Delete legacy `generate_pdf()`. Merge `GeneratePDFAPI.generate_student_result_pdf()` into `GenerateStudentResultPDFAPI`.
* **Validation:** Generate both PDF types via API. Confirm layout matches current output.

### Step 7 — Delete All Remaining Legacy Views (V09, R01–R07, R10, R12)

* **Target Files:** Modified: `views.py`, `urls.py`.
* **Action:** Delete all legacy view functions that are fully duplicated by API endpoints: `upload_grades`, `upload_grades_prof`, `moderate_student_grades`, `generate_pdf`, `generate_result`, `Updatehidden_gradesMultipleView`, `Submithidden_gradesMultipleView`, `DownloadExcelView`, `updateGrades`. Remove corresponding URL routes.
* **Validation:** Confirm each deleted URL returns 404. Confirm API equivalents work.

### Step 8 — Fix Authentication Permissions (V14–V17)

* **Target Files:** Modified: `views.py`.
* **Action:** Replace all `permission_classes = [AllowAny]` with `[IsAuthenticated]` on grade-modifying endpoints.
* **Validation:** Unauthenticated request returns 401. Authenticated request works as before.

### Step 9 — Fix Role Authorization (V18)

* **Target Files:** New: `permissions.py`. Modified: `api/views.py`.
* **Action:** Create `permissions.py` with server-side role permission classes. Replace all `request.data.get("Role")` authorization with `HoldsDesignation` lookups.
* **Validation:** Send request with fake `"Role": "acadadmin"` — confirm 403. Send with legitimate user — confirm 200.

### Step 10 — Fix Input Validation & Error Handling (V19–V22)

* **Target Files:** Modified: `api/views.py`.
* **Action:** Add file size limits, wrap `json.loads` in try/except, replace bare `except:` with specific exception classes.
* **Validation:** Send malformed input to each endpoint — confirm proper 400 response instead of 500.

### Step 11 — Fix Serializers (V23, V24)

* **Target Files:** Modified: `api/serializers.py`.
* **Action:** Fix `AuthenticationSerializer` model reference. Create and use proper serializers for all API endpoints.
* **Validation:** `.is_valid()` returns `False` for bad input, `True` for good input.

### Step 12 — Remove Dead Code (V25–V29)

* **Target Files:** Modified: `views.py`.
* **Action:** Remove all unreachable code. Rename shadowed `Student_grades` variable in `submitEntergradesStoring` to `student_grades_list`.
* **Validation:** Endpoint no longer throws `AttributeError`. No behavioral change from dead code removal.

### Step 13 — Extract Constants (V30, V31)

* **Target Files:** New: `constants.py`. Modified: `api/views.py`, `views.py`.
* **Action:** Create `constants.py` with all role strings, programme type mappings, and grade constants. Replace all hardcoded literals.
* **Validation:** `grep` for raw role/programme strings returns 0 hits in views files.

### Step 14 — Fix N+1 Queries (V32, V33, V34)

* **Target Files:** Modified: `api/views.py` (or `selectors.py` after extraction).
* **Action:** Prefetch User records, prefetch all `Student_grades` and `course_registration` before loops, prefetch `course_replacement` for BFS.
* **Validation:** Use Django debug toolbar or `connection.queries` to confirm query count drops from O(n) to O(1).

### Step 15 — Model Renaming (V35)

* **Target Files:** Modified: `models.py`, all files referencing models.
* **Action:** Rename models to PascalCase with `db_table` meta.
* **Validation:** `makemigrations` produces no schema-changing migration.

### Step 16 — URL & Deprecated API Cleanup (V36, V40, V41, V42)

* **Target Files:** Modified: `urls.py`, `api/urls.py`, `views.py`.
* **Action:** Standardize URLs to kebab-case; replace `url()` with `path()`; remove `print()` statements; replace `request.is_ajax()` with header check.
* **Validation:** All URLs resolve. AJAX detection still works. No console output.

### Step 17 — Replace Raw SQL (V39)

* **Target Files:** Modified: `api/views.py`.
* **Action:** Replace raw SQL in `GradeSummaryAPI` with ORM aggregation.
* **Validation:** Compare JSON output before/after — identical results.

---

## Section 5: API Audit

### 5A — Active APIs (`api/urls.py`)

| No. | URL                              | Method   | View                            | Auth            | Status          | Fix Plan           |
| --- | -------------------------------- | -------- | ------------------------------- | --------------- | --------------- | ------------------ |
| 1   | `exam_view/`                   | POST     | `exam_view`                   | IsAuthenticated | ⚠️ WARN       | V18                |
| 2   | `download_template/`           | POST     | `download_template`           | IsAuthenticated | ⚠️ WARN       | V18                |
| 3   | `check_course_students/`       | POST     | `check_course_students`       | IsAuthenticated | ⚠️ WARN       | V18                |
| 4   | `submitGrades/`                | POST     | `SubmitGradesView`            | IsAuthenticated | ⚠️ WARN       | V18, V24           |
| 5   | `upload_grades/`               | POST     | `UploadGradesAPI`             | IsAuthenticated | ⚠️ WARN       | V18, V04, V24      |
| 6   | `update_grades/`               | POST     | `UpdateGradesAPI`             | IsAuthenticated | ⚠️ WARN       | V18                |
| 7   | `update_enter_grades/`         | POST     | `UpdateEnterGradesAPI`        | IsAuthenticated | ⚠️ WARN       | V18                |
| 8   | `moderate_student_grades/`     | POST     | `ModerateStudentGradesAPI`    | IsAuthenticated | ⚠️ WARN       | V18                |
| 9   | `generate_transcript/`         | POST     | `GenerateTranscript`          | IsAuthenticated | ⚠️ WARN       | V18, V20, V21      |
| 10  | `generate_transcript_form/`    | GET/POST | `GenerateTranscriptForm`      | IsAuthenticated | ⚠️ WARN       | V18                |
| 11  | `generate_result/`             | POST     | `GenerateResultAPI`           | IsAuthenticated | ⚠️ WARN       | V18, V06, V32, V33 |
| 12  | `submit/`                      | POST     | `SubmitAPI`                   | IsAuthenticated | ⚠️ WARN       | V18                |
| 13  | `download_excel/`              | POST     | `DownloadExcelAPI`            | IsAuthenticated | 🚨 NON-STANDARD | Add role check     |
| 14  | `submitGradesProf/`            | POST     | `SubmitGradesProfAPI`         | IsAuthenticated | ⚠️ WARN       | V18                |
| 15  | `upload_grades_prof/`          | POST     | `UploadGradesProfAPI`         | IsAuthenticated | ⚠️ WARN       | V18                |
| 16  | `generate_pdf/`                | POST     | `GeneratePDFAPI`              | IsAuthenticated | ⚠️ WARN       | V18, V38           |
| 17  | `generate_student_result_pdf/` | POST     | `GenerateStudentResultPDFAPI` | IsAuthenticated | 🚨 NON-STANDARD | Add role check     |
| 18  | `downloadGrades/`              | POST     | `DownloadGradesAPI`           | IsAuthenticated | ⚠️ WARN       | V18                |
| 19  | `verify_grades_dean/`          | POST     | `VerifyGradesDeanView`        | IsAuthenticated | ⚠️ WARN       | V18                |
| 20  | `update_enter_grades_dean/`    | POST     | `UpdateEnterGradesDeanView`   | IsAuthenticated | ⚠️ WARN       | V18                |
| 21  | `validate_dean/`               | POST     | `ValidateDeanView`            | IsAuthenticated | ⚠️ WARN       | V18                |
| 22  | `validate_dean_submit/`        | POST     | `ValidateDeanSubmitView`      | IsAuthenticated | ⚠️ WARN       | V18                |
| 23  | `check_result/`                | POST     | `CheckResultView`             | IsAuthenticated | ✅ OK           | —                 |
| 24  | `preview_grades/`              | POST     | `PreviewGradesAPI`            | IsAuthenticated | ⚠️ WARN       | V18                |
| 25  | `result-announcements/`        | GET      | `ResultAnnouncementListAPI`   | IsAuthenticated | ⚠️ WARN       | V18                |
| 26  | `update-announcement/`         | POST     | `UpdateAnnouncementAPI`       | IsAuthenticated | ⚠️ WARN       | V18                |
| 27  | `create-announcement/`         | POST     | `CreateAnnouncementAPI`       | IsAuthenticated | ⚠️ WARN       | V18                |
| 28  | `unique-course-reg-years/`     | GET      | `UniqueRegistrationYearsView` | IsAuthenticated | ✅ OK           | —                 |
| 29  | `unique-stu-grades-years/`     | GET      | `UniqueStudentGradeYearsView` | IsAuthenticated | ✅ OK           | —                 |
| 30  | `student/result_semesters/`    | GET      | `StudentSemesterListView`     | IsAuthenticated | ✅ OK           | —                 |
| 31  | `grade_status/`                | POST     | `GradeStatusAPI`              | IsAuthenticated | ⚠️ WARN       | V18                |
| 32  | `grade_summary/`               | POST     | `GradeSummaryAPI`             | IsAuthenticated | ⚠️ WARN       | V18, V39           |

---

### 5B — Inactive/Commented-Out APIs (`urls.py`)

| No. | URL                                | View                                | Action                                                      |
| --- | ---------------------------------- | ----------------------------------- | ----------------------------------------------------------- |
| 1   | `verify/`                        | `views.verify`                    | Remove; functionality covered by `verify_grades_dean/`API |
| 2   | `publish/`                       | `views.publish`                   | Remove; empty template render                               |
| 3   | `notReady_publish/`              | `views.notReady_publish`          | Remove; empty template render                               |
| 4   | `timetable/`                     | `views.timetable`                 | Remove; empty template render                               |
| 5   | `entergrades/`                   | `views.entergrades`               | Remove; covered by API upload endpoints                     |
| 6   | `update_hidden_grades_multiple/` | `Updatehidden_gradesMultipleView` | Remove; superseded by `ModerateStudentGradesAPI`          |
| 7   | `submit_hidden_grades_multiple/` | `Submithidden_gradesMultipleView` | Remove                                                      |
| 8   | `verifygrades/`                  | `views.verifygrades`              | Remove                                                      |
| 9   | `submitEntergrades/`             | `views.submitEntergrades`         | Remove                                                      |
| 10  | `submitEntergradesStoring/`      | `views.submitEntergradesStoring`  | Remove                                                      |
| 11  | `authenticate/`                  | `views.authenticate`              | Remove                                                      |
| 12  | `authenticategrades/`            | `views.authenticategrades`        | Remove                                                      |
| 13  | `update_authentication/`         | `update_authentication.as_view()` | Remove                                                      |
| 14  | `checkresult/`                   | `views.checkresult`               | Remove; covered by `check_result/`API                     |
| 15  | `grades_report/`                 | `views.grades_report`             | Remove; covered by `check_result/`API                     |

---

### 5C — API Compliance Checklist

| Check                            | Status       | Details                                                                                               |
| -------------------------------- | ------------ | ----------------------------------------------------------------------------------------------------- |
| Uses `@api_view`or `APIView` | ⚠️ Partial | API views use `APIView`or `@api_view`. Legacy views are not DRF-compliant.                        |
| Uses `permission_classes`      | ⚠️ Partial | All API views set `[IsAuthenticated]`. 4 legacy APIViews use `AllowAny`(V14–V17).                |
| Uses `authentication_classes`  | ❌ NO        | No view explicitly sets `authentication_classes`. Relies on DRF defaults. Should be explicit.       |
| Uses DRF `Response`            | ⚠️ Partial | API views use `Response()`. Some use `JsonResponse`inconsistently. Legacy views use `render()`. |
| Uses serializers for input       | ❌ NO        | Zero endpoints use serializers for input validation. All manually extract `request.data.get(...)`.  |
| Uses serializers for output      | ❌ NO        | Zero endpoints use serializers for output. All manually construct `Response({...})`dicts.           |
| Consistent error format          | ❌ NO        | At least 5 different error formats in use across the codebase.                                        |
| Pagination present               | ❌ NO        | No endpoint uses pagination. Unbounded result sets.                                                   |
| API versioning                   | ❌ NO        | No versioning scheme (`v1/`prefix or header-based).                                                 |
| URL naming consistency           | ❌ NO        | Mix of camelCase, snake_case, and kebab-case with inconsistent trailing slashes.                      |

---

### 5D — Legacy Views Requiring API Migration

| No. | Function                       | URL                                       | Needs API                                                          |
| --- | ------------------------------ | ----------------------------------------- | ------------------------------------------------------------------ |
| 1   | `exam()`                     | `examination/`                          | Yes — equivalent:`exam_view`API                                 |
| 2   | `submit()`                   | `examination/submit/`                   | Yes — equivalent:`SubmitAPI`                                    |
| 3   | `updateGrades()`             | `examination/updateGrades/`             | Yes — equivalent:`UpdateGradesAPI`                              |
| 4   | `updateEntergrades()`        | `examination/updateEntergrades/`        | Yes — equivalent:`UpdateEnterGradesAPI`                         |
| 5   | `submitGradesProf()`         | `examination/submitGradesProf/`         | Yes — equivalent:`SubmitGradesProfAPI`                          |
| 6   | `upload_grades()`            | `examination/upload_grades/`            | Yes — equivalent:`UploadGradesAPI`                              |
| 7   | `upload_grades_prof()`       | `examination/upload_grades_prof/`       | Yes — equivalent:`UploadGradesProfAPI`                          |
| 8   | `download_template()`        | `examination/download_template/`        | Yes — equivalent:`download_template`API                         |
| 9   | `generate_transcript()`      | `examination/generate_transcript/`      | Yes — equivalent:`GenerateTranscript`API                        |
| 10  | `generate_transcript_form()` | `examination/generate_transcript_form/` | Yes — equivalent:`GenerateTranscriptForm`API                    |
| 11  | `moderate_student_grades`    | `examination/moderate_student_grades/`  | Yes — equivalent:`ModerateStudentGradesAPI`                     |
| 12  | `verifyGradesDean()`         | `examination/verifyGradesDean/`         | Yes — equivalent:`VerifyGradesDeanView`API                      |
| 13  | `updateEntergradesDean()`    | `examination/updateEntergradesDean/`    | Yes — equivalent:`UpdateEnterGradesDeanView`API                 |
| 14  | `validateDean()`             | `examination/validateDean/`             | Yes — equivalent:`ValidateDeanView`API                          |
| 15  | `validateDeanSubmit()`       | `examination/validateDeanSubmit/`       | Yes — equivalent:`ValidateDeanSubmitView`API                    |
| 16  | `downloadGrades()`           | `examination/downloadGrades/`           | Yes — equivalent:`DownloadGradesAPI`                            |
| 17  | `generate_pdf()`             | `examination/generate_pdf/`             | Yes — equivalent:`GeneratePDFAPI`                               |
| 18  | `generate_result()`          | `examination/generate-result/`          | Yes — equivalent:`GenerateResultAPI`                            |
| 19  | `show_message()`             | `examination/message/`                  | No — utility page; can be handled frontend-side                   |
| 20  | `announcement()`             | `examination/announcement/`             | Yes — use `ResultAnnouncementListAPI`/`CreateAnnouncementAPI` |
| 21  | `download_excel/`            | `examination/download_excel/`           | Yes — equivalent:`DownloadExcelAPI`                             |

---

## Summary of Critical Findings

> **Authorization is fundamentally broken (V18):** All 28+ API endpoints accept a client-supplied `Role` parameter for authorization. An attacker with any valid auth token can claim `"Role": "acadadmin"` and gain full access to grade modification, transcript generation, and result publishing. **This is the highest-priority fix.**

> **Four endpoints use `AllowAny` (V14–V17):** Grade modification endpoints in `views.py` are accessible without any authentication at all.

> **No tests exist (V03):** Zero test coverage for a module handling student grades — the most sensitive academic data in the system.

> **Massive duplication:** 18 legacy views duplicate functionality already available in API views (R01–R12). The module carries ~1,950 lines of dead-weight legacy code.

> **5,717 lines of views with zero service/selector layer:** All business logic, ORM queries, PDF/Excel generation, and CSV parsing are embedded directly in view functions, making the code untestable and unmaintainable.
>
