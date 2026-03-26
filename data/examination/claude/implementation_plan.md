# Examination Module Refactoring — Implementation Plan

Refactor the examination module to comply with the target architecture: thin views, services for business logic, selectors for DB queries, proper serializers, and DRF-compliant APIs. All 42 structural violations (V01–V42) and 12 redundancies (R01–R12) from the audit report are addressed.

> [!IMPORTANT]
> **No logic changes.** All business logic is relocated exactly as-is. No schema migrations are generated. API inputs/outputs remain identical.

---

## Proposed Changes

### Constants Layer

#### [NEW] [constants.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/constants.py)
- Move `grade_conversion`, `ALLOWED_GRADES`, `PBI_AND_BTP_ALLOWED_GRADES` from [api/views.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/api/views.py) (V13, V30)
- Define role constants: `ROLE_ACADADMIN`, `ROLE_DEAN_ACADEMIC`, `PROFESSOR_ROLES`, `ALL_ALLOWED_ROLES` (V30)
- Define programme type constants: `UG_PROGRAMMES`, `PG_PROGRAMMES` (V31)
- Define `MAX_CSV_FILE_SIZE = 5 * 1024 * 1024` and `MAX_CSV_ROW_COUNT = 10000` (V19)

---

### Selector Layer

#### [NEW] [selectors.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/selectors.py)
- `get_unverified_courses(academic_year, semester_type)` — used by [UpdateGradesAPI](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/api/views.py#781-831) (V02)
- `get_verified_courses()` — used by [ValidateDeanView](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/api/views.py#2638-2678), [VerifyGradesDeanView](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/api/views.py#2510-2537) (V02, R11)
- `get_student_grades_for_semester(roll_no, semester, semester_type)` — used by transcript/result endpoints
- `get_course_registrations(course_id, session, semester_type)` — shared filter
- `get_students_by_programme_type(programme_type)` — consolidates 7+ duplicate programme filter blocks (R09)
- `get_instructor_courses(instructor_id, working_year, semester_type)` — used by [SubmitGradesProfAPI](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/api/views.py#1599-1701), [DownloadGradesAPI](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/api/views.py#2002-2064)
- `get_grades_for_course(course_id, academic_year, semester_type)` — used across multiple views
- `get_running_batches()` — used by [GenerateTranscriptForm](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/api/views.py#1169-1236), [ResultAnnouncementListAPI](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/api/views.py#3042-3087)
- `get_student_by_roll(roll_no)` — wraps `Student.objects.get(id_id=...)`
- `get_unique_academic_years()` and `get_unique_registration_years(programme_type=None)`
- All ORM `.objects.*` calls from views are moved here (V02, 120+ queries)

---

### Service Layer

#### [NEW] [services.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/services.py)
- Move [calculate_spi_for_student()](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/api/views.py#97-129), [calculate_cpi_for_student()](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/api/views.py#137-216) from `api/views.py:97–215` (V12)
- Move [trace_registration()](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/api/views.py#130-136), [round_from_last_decimal()](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/api/views.py#80-95), [gather_related_registrations()](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/api/views.py#255-275) (V12)
- Move [parse_academic_year()](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/api/views.py#217-238), [is_valid_grade()](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/api/views.py#239-253), [format_semester_display()](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/api/views.py#63-79), [make_label()](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/api/views.py#3171-3182) (V12)
- [upload_grades(course_id, academic_year, semester_type, csv_data)](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/views.py#917-1040) — extracted from `UploadGradesAPI.post()` (V04)
- [upload_grades_prof(course_id, academic_year, semester_type, csv_data, instructor_id, programme_type)](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/views.py#1210-1333) — extracted from `UploadGradesProfAPI.post()` (V05)
- `generate_result_excel(students, courses, semester, semester_type, batch_obj)` — extracted from `GenerateResultAPI.post()` (V06)
- `generate_course_grade_pdf(course_info, grades, instructor, academic_year)` — extracted from `GeneratePDFAPI.post()` faculty branch (V07)
- [generate_student_result_pdf(student_info, courses, spi, cpi, su, tu, semester_no, semester_type, semester_label, is_transcript=False)](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/api/views.py#2293-2469) — consolidated from both `GeneratePDFAPI.generate_student_result_pdf()` and `GenerateStudentResultPDFAPI.post()` (V08, R06)
- `moderate_grades(student_ids, semester_ids, course_ids, grades, remarks, allow_resubmission)` — extracted from [ModerateStudentGradesAPI](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/api/views.py#953-1024)
- `validate_dean_csv(csv_file, course_id, academic_year)` — extracted from [ValidateDeanSubmitView](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/api/views.py#2680-2800)
- `compute_grade_points(grade_str)` — uses `grade_conversion` dict instead of if/elif chains (R08)
- Fix N+1: prefetch users, grades, registrations before loops (V32, V33, V34)
- Replace raw SQL in [GradeSummaryAPI](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/api/views.py#3679-3765) with ORM aggregation (V39)

---

### Permissions Layer

#### [NEW] [permissions.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/permissions.py)
- `IsAcadAdmin` — checks `HoldsDesignation` for acadadmin (V18)
- `IsDeanAcademic` — checks for Dean Academic
- `IsProfessor` — checks for professor roles
- `IsAcadAdminOrDean` — combination
- `IsAcadAdminOrProfessor` — combination
- All replace `request.data.get("Role")` checks (V14–V18)

---

### Models

#### [MODIFY] [models.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/models.py)
- Rename [hidden_grades](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/models.py#9-17) → `HiddenGrade` with `class Meta: db_table = 'examination_hidden_grades'` (V35)
- Rename [authentication](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/models.py#19-33) → [Authentication](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/api/serializers.py#19-23) with `class Meta: db_table = 'examination_authentication'` (V35)
- Rename [grade](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/models.py#35-40) → [Grade](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/views.py#615-647) with `class Meta: db_table = 'examination_grade'` (V35)
- [ResultAnnouncement](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/models.py#41-50) stays as-is (already PascalCase)
- Add [__str__](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/models.py#47-50) to [Grade](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/views.py#615-647) model

---

### Serializers

#### [MODIFY] [api/serializers.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/api/serializers.py)
- Fix `AuthenticationSerializer.Meta.model` from [Announcements](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/api/serializers.py#14-18) to [Authentication](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/api/serializers.py#19-23) (V23)
- Add proper input serializers for endpoints that need validation (V24):
  - `ExamViewInputSerializer` (role)
  - `UploadGradesInputSerializer` (course_id, academic_year, semester_type, csv_file)
  - `GradeDataInputSerializer` (student_ids, semester_ids, course_ids, grades)
  - `TranscriptInputSerializer` (student, semester)
  - `GenerateResultInputSerializer` (semester, batch, specialization)
  - `AnnouncementInputSerializer` (batch, semester)
  - `SemesterInputSerializer` (semester_no, semester_type)
  - `AcademicYearSemesterInputSerializer` (academic_year, semester_type)

---

### API Views

#### [MODIFY] [api/views.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/api/views.py)
- Remove all module-level helper functions (moved to services/constants)
- Remove all inline ORM queries (moved to selectors)
- All views become thin: parse request → validate with serializer → call service → return response
- Replace `request.data.get("Role")` authorization with `permission_classes` from `permissions.py` (V18)
- Use `IsAuthenticated` on all endpoints (already present but role checks move to permissions)
- Fix bare `except:` on lines 1078, 1414 (V21, V22)
- Add `json.loads` try/except for [GenerateTranscript](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/api/views.py#1057-1131) (V20)
- Add file size limit check in upload views (V19)
- Split `GeneratePDFAPI.post()` — remove student PDF dispatch; that's handled by [GenerateStudentResultPDFAPI](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/api/views.py#3362-3678) only (V38)
- [GenerateStudentResultPDFAPI](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/api/views.py#3362-3678) calls shared `services.generate_student_result_pdf()` (R06)
- Use DRF `Response` everywhere (not `JsonResponse`) for consistency
- Replace `traceback.print_exc()` with `logging.exception()`

---

### API URLs

#### [MODIFY] [api/urls.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/api/urls.py)
- Replace `url()` with `path()` (V40)
- Standardize all URLs to kebab-case (V36)

---

### Legacy Views & URLs

#### [MODIFY] [views.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/views.py)
- Remove all legacy views duplicated by API endpoints (R01–R05, R07, R10, R12):
  - [upload_grades](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/views.py#917-1040) (R01), [upload_grades_prof](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/views.py#1210-1333) (R02), [moderate_student_grades](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/views.py#680-728) (R03), [generate_pdf](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/views.py#1526-1697) (R04), [generate_result](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/views.py#1699-1875) (R05), [Updatehidden_gradesMultipleView](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/views.py#370-409)/[Submithidden_gradesMultipleView](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/views.py#411-440) (R07), [updateGrades](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/views.py#615-647) (R10), [DownloadExcelView](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/views.py#482-501) (R12)
- Remove dead code: unreachable returns on lines 408, 727, 782, 915 (V25–V28)
- Fix variable shadowing: `Student_grades` on line 816 → `student_grades_list` (V29)
- Remove `print()` statements (V41)
- Replace `request.is_ajax()` with header check (V42)
- Fix `AllowAny` permissions → `IsAuthenticated` (V14–V17)
- Keep only template-serving views that have no API equivalent: [exam](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/views.py#75-102), [submit](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/views.py#104-123), [show_message](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/views.py#1041-1060), [announcement](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/views.py#311-368), [generate_transcript](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/views.py#502-571), [generate_transcript_form](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/views.py#574-613), [submitGradesProf](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/views.py#1062-1099), [download_template](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/views.py#1100-1150), [verifyGradesDean](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/views.py#1152-1184), [updateEntergrades](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/views.py#648-679), [updateEntergradesDean](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/views.py#1185-1208), [validateDean](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/views.py#1335-1365), [validateDeanSubmit](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/views.py#1366-1477), [downloadGrades](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/views.py#1478-1524), [submitGrades](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/views.py#730-771), [checkresult](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/views.py#1876-1886)
- These remaining legacy views should use services/selectors instead of inline queries

#### [MODIFY] [urls.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/urls.py)
- Replace `url()` with `path()` (V40)
- Remove routes for deleted views
- Remove commented-out routes

---

### Admin & Apps

#### [MODIFY] [admin.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/admin.py)
- Update imports for renamed PascalCase models

#### [MODIFY] [apps.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/apps.py)
- Add `default_auto_field = 'django.db.models.BigAutoField'`

---

### Tests

#### [NEW] [tests/\_\_init\_\_.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/tests/__init__.py)
#### [NEW] [tests/test_module.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/tests/test_module.py)
- Unit tests for service functions (SPI/CPI calculation, grade validation, academic year parsing)
- Unit tests for selector functions
- Integration tests for key API endpoints (upload grades, generate transcript, check result)
- Edge case tests (missing roles, invalid grades, nonexistent students)
- Test permission classes reject unauthenticated/unauthorized access

#### [DELETE] [tests.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/tests.py)

---

## Verification Plan

### Automated Tests

Run the examination module tests:
```bash
cd c:\Users\sujit\OneDrive\Documents\Fusion_new\Fusion\FusionIIIT
python manage.py test applications.examination.tests --verbosity=2
```

### Static Verification

Verify no raw role strings remain in views:
```bash
grep -rn '"acadadmin"' applications/examination/api/views.py applications/examination/views.py
grep -rn '"Dean Academic"' applications/examination/api/views.py applications/examination/views.py
grep -rn 'request.data.get.*Role' applications/examination/api/views.py
```

Verify no inline ORM queries in views:
```bash
grep -rn '\.objects\.' applications/examination/api/views.py | grep -v 'import'
```

Verify no `print()` statements:
```bash
grep -rn 'print(' applications/examination/views.py applications/examination/api/views.py
```

Verify no deprecated `url()`:
```bash
grep -rn 'from django.conf.urls import url' applications/examination/urls.py applications/examination/api/urls.py
```

### Manual Verification
> [!NOTE]
> Since this project requires a full Django environment with database setup and dependent apps (`academic_procedures`, `programme_curriculum`, `online_cms`, `academic_information`), full integration testing requires the user to run the dev server and verify endpoints manually. The automated tests will use Django's `TestCase` with mock data.
