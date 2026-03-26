# Examination Module: Structural Audit & Refactoring Plan

## SECTION 1: MODULE SNAPSHOT

| Metric | Value | Measurement Method |
| :--- | :--- | :--- |
| **Total LOC (approx.)** | 5,989 | Counted lines across all [.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/apps.py) files in the module recursively |
| **LOC in views.py** | 1,953 | Counted lines directly in [views.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/views.py) |
| **LOC in api/views.py** | 3,764 | Counted lines directly in [api/views.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/api/views.py) |
| **No. of service files** | 0 | Checked module directory structure; `services.py` is absent |
| **No. of serializer classes** | 3 | Traversed [api/serializers.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/api/serializers.py) identifying derived classes |
| **No. of models** | 4 | Counted model classes defined in [models.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/models.py) |
| **Number of API endpoints** | 33 | Parsed `path`/`url` references in [api/urls.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/api/urls.py) |
| **Number of DB queries in views** | 221 | Parsed AST for `.objects.`, `.save()`, `.delete()` calls inside [views.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/views.py) & [api/views.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/api/views.py) |
| **No. of structural violations** | 76 | Counted functions/methods matching Fat View, Logic in Views, or Mixed Responsibilities |
| **No. of redundancy items** | 15+ | Detected cross-referencing duplicate methods across web [views.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/views.py) and [api/views.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/api/views.py) |
| **services.py exists (Y/N)** | N | Validated missing file via file-system listing |
| **selectors.py exists (Y/N)** | N | Validated missing file via file-system listing |
| **tests/ folder exists (Y/N)** | N | Validated missing folder (only basic [tests.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/tests.py) present) |
| **api/ folder exists (Y/N)** | Y | Exists containing [serializers.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/api/serializers.py), [urls.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/urls.py), and [views.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/views.py) |
| **Uses TextChoices (Y/N)** | N | Scanned [models.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/models.py); status/grades rely on hardcoded CharFields with defaults |
| **Overall Structural State** | Poor | Massive views, highly coupled, business logic bleeding into controllers |

---

## SECTION 2: STRUCTURAL AUDIT

| ID | Category | File | Line Range | Description | Impact | Planned Fix | Detailed Fix Steps |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 01 | Missing Folder Structure | Overall | N/A | Missing `services.py` & `selectors.py`. Model queries exist directly in controllers. | HIGH | Migrate Architecture | Create layered files. Migrate all business rules to services. |
| 02 | Mixed Responsibilities | [views.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/views.py) | 806-915 | `submitEntergradesStoring` executes DB saving, redirects, and rendering concurrently. | HIGH | Delegate Logic | Move storage logic to `examination_service.submit_grades()`. View simply acts as router. |
| 03 | Fat View | [views.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/views.py) | 918-1039 | `upload_grades` exceeds 120 lines, heavily entangled with excel parsing and db creation. | HIGH | Extract Logic | Move parsing to formatting util, save operations to `submit_grades` service. |
| 04 | Fat View | [views.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/views.py) | 1367-1476 | `validateDeanSubmit` merges workflow validation and model state updates. | HIGH | Decouple Validation | Move dean verification rules into `DeanValidationService`. View just calls `.execute()`. |
| 05 | Fat View | [views.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/views.py) | 1527-1696 | `generate_pdf` handles heavy business logic to accumulate result datasets. | HIGH | Extract Logic | Push data aggregation to `ReportSelector` and generation to `ReportService`. |
| 06 | Fat View | [views.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/views.py) | 1700-1874 | `generate_result` has 175 lines, 9 queries computing grade logic. | CRITICAL | Move to Service | Extract grade calculation into a dedicated `GradeCalculationService`. |
| 07 | Legacy Code Leak | [api/views.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/api/views.py) | 137-215 | `calculate_cpi_for_student` API contains 79 lines of core calculation logic. | HIGH | Extract Logic | Move mathematical logic to `calculation_service.py` to be shared. |
| 08 | Fat View | [api/views.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/api/views.py) | 353-469 | `download_template` builds heavy custom responses and reads multiple models. | HIGH | Extract Logic | Delegate to `DownloadTemplateService` to construct dataset. |
| 09 | Logic in Serializer | [api/views.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/api/views.py) | 592-755 | `UploadGradesAPI` handles 6 DB writes inside logic rather than using a proper serializer `create` or service. | HIGH | Refactor POST | Bind Excel validation to an active serializer, execute save via Service. |
| 10 | Fat View | [api/views.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/api/views.py) | 953-1023 | `ModerateStudentGradesAPI` modifies multiple grades. Entangled permission checks. | HIGH | Decouple Logic | Use serializer for body validation. Push bulk update logic to Service. |
| 11 | Fat View | [api/views.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/api/views.py) | 1238-1493 | `GenerateResultAPI` consists of 256 lines and 10 queries. | CRITICAL | Move to Service | Completely rip logic into `ResultComputationService` and leave purely I/O in API view. |
| 12 | Fat View | [api/views.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/api/views.py) | 1703-1999 | `UploadGradesProfAPI` repeats 297 lines of parsing logic handling 10 DB writes. | HIGH | Refactor & DRY | Consolidate with other UploadGrade implementations in shared service. |
| 13 | Cross-Module Tight Coupling | [models.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/models.py) | 1-5 | Direct imports from `applications.academic_procedures`, `online_cms`. Expected but tightly bounds examination to them. | MEDIUM | Standardize Interfaces | Keep foreign keys but wrap data retrieval in cross-module selectors. |
| 14 | Hard-coded Values | [models.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/models.py) | 39 | `grade = models.CharField(max_length=5, default="B")` | LOW | Use TextChoices | Replace hard-coded string with `class Grades(models.TextChoices)`. |
| 15 | Hard-coded Values | [models.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/models.py) | 25 | `course_year = models.IntegerField(default=2024)` | MEDIUM | Dynamic Logic | Rely on dynamic service layer logic or function for year calculation, not hardcode. |
| 16 | Missing Input Validation | [api/views.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/api/views.py) | Overall | High percentage of APIs retrieve payload `request.data.get('X')` directly without a validating Serializer layer. | CRITICAL | Introduce Serializer | Define proper Serializers with field validations for every POST endpoint. |

---

## SECTION 3: REDUNDANCY REGISTER

| ID | Type | Location 1 | Location 2 | Description | Redundant | Plan | Detailed Consolidation |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| R01 | Code | `views.py:submitGrades` | `api/views.py:SubmitGradesView` | Handling basic submission logic for grades. | Yes | Consolidate to Service | Both points to call `GradeSubmissionService.submit()`. Legacy view wraps response. |
| R02 | Code | `views.py:upload_grades` | `api/views.py:UploadGradesAPI` | Handling excel grading sheet parsing and DB updates. | Yes | Consolidate to Service | Unify logic in `GradeExcelParserService.parse_and_save()`. |
| R03 | Concept | `api/views.py:UploadGradesAPI` | `api/views.py:UploadGradesProfAPI` | Separate endpoints for what looks like the same core upload action for different roles. | Yes | Unify Endpoint/Service | Determine role in a single view or rely on shared `UploadService` if separate endpoints retained. |
| R04 | Concept | `views.py:generate_transcript` | `api/views.py:GenerateTranscript` | Transcript data generation duplicated across legacy web and API view. | Yes | Consolidate to Service | Both layers to hit `TranscriptService.generate()`. |
| R05 | Query | `views.py:generate_result` | `api/views.py:GenerateResultAPI` | Complex DB joins/reads checking result statuses over 150+ lines. | Yes | Extract Selector | Move complex result checks to `ResultSelector.get_student_results()`. |
| R06 | Code | `views.py:generate_pdf` | `api/views.py:GenerateStudentResultPDFAPI` | PDF generator logic implemented directly in views duplicating template variables. | Yes | Extract Service | Move template population & rendering into `PDFGenerationService`. |
| R07 | Code | `views.py:updateEntergrades` | `api/views.py:UpdateEnterGradesAPI` | DB query updates for entering single grades. | Yes | Consolidate | Update logic moves to `GradeUpdateService.update()`. |
| R08 | Code | `views.py:validateDean` | `api/views.py:VerifyGradesDeanView` | Validating the state of dean verified grades. | Yes | Consolidate | Merge workflow logic into `DeanWorkflowService`. |

---

## SECTION 4: REFACTORING PLAN

| Ref IDs | Action | Target Files | Validation |
| :--- | :--- | :--- | :--- |
| 01 | Setup Architecture baseline | `services.py`, `selectors.py`, `tests/` | Manual verification that `manage.py check` passes and folder is created. |
| 14, 15 | Update Models to standards | [models.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/models.py) | Unit tests on Model instantiation asserting correct TextChoices mapping. |
| 06, 07, 11 | Migrate Grade/CPI math logic to independent functions | `services.py`, `selectors.py` | Unit tests to ensure `calculate_cpi_for_student` yields exact same math. |
| 16 | Define robust serializers | [api/serializers.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/api/serializers.py) | API validation tests mapping invalid payload cases resulting in 400 Bad Request. |
| 02, 09, R01 | Extract "Submit Grade" logic to Service Layer | [views.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/views.py), [api/views.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/api/views.py), `services.py` | Form submission and API integration tests tracking proper DB grade update behavior. |
| 03, 12, R02, R03 | Consolidate "Upload Excel Grade" capabilities | `services.py`, [views.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/views.py), [api/views.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/api/views.py) | Data integrity tests uploading mockup `.xlsx` formats via client ensuring no duplicates. |
| 04, R08 | Move "Dean Workflow" validation into Service | `services.py`, [views.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/views.py), [api/views.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/api/views.py) | State transition unit tests asserting Grade blocks pending dean validation. |
| 05, R04, R06 | Refactor Report/PDF generation | `services.py`, [views.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/views.py), [api/views.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/api/views.py) | Byte comparison (or PDF scraping) manual test indicating visual parity before/after target change. |
| All | Complete End-to-end integration tests over new endpoints | `tests/test_api.py` | API TestSuite executed via `pytest`, targeting 90% endpoint path coverage minimum. |

---

## SECTION 5: API AUDIT

### 5A - Active APIs

| No. | URL | Method | View | Auth | Role Check | Serializer | Status | Validation | Fix Plan |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | `submitGrades/` | POST | `SubmitGradesView` | Mixed | WARN | None | CRITICAL | No strict DRF Serializer | Abstract body `request.data` validation to `GradeSubmissionSerializer` |
| 2 | `upload_grades/` | POST | `UploadGradesAPI` | Mixed | WARN | None | CRITICAL | Internal `MultiPartParser` rules used directly | Implement explicit DRF wrapper for Excel parsing validation |
| 3 | `update_grades/` | POST | `UpdateGradesAPI` | Mixed | WARN | None | NON-STANDARD | No true Request Validator | Add validationSerializer, rely on Update model actions |
| 4 | `generate_result/` | POST | `GenerateResultAPI` | Mixed | WARN | None | CRITICAL | Fat View, raw `request.data.get('x')` | Pass explicit body requirements through DRF serialization layer |
| 5 | `generate_transcript/`| POST | `GenerateTranscript` | Mixed | WARN | None | NON-STANDARD | Direct parameter grabbing | Apply query parameter validation |
| 6 | `preview_grades/` | POST | `PreviewGradesAPI` | Mixed | WARN | None | NON-STANDARD | N/A | Provide payload schema |
| 7 | `grade_status/` | POST | `GradeStatusAPI` | Mixed | WARN | None | CRITICAL | Payload fetching inline | Move fetching into nested serializers |
| 8 | `create-announcement/`| POST | `CreateAnnouncementAPI` | Mixed | WARN | None | NON-STANDARD | Logic hidden in View | Wire to DRF standard `CreateAPIView` |
| 9 | `result-announcements/`| GET | `ResultAnnouncementListAPI`| Mixed | WARN | None | NON-STANDARD | Custom logic to list | Refactor to standard `ListAPIView` with filtering applied |

### 5B - Inactive APIs

| No. | URL | View | Status | Action |
| :--- | :--- | :--- | :--- | :--- |
| 1 | `checkresult/` | `checkresult` (legacy views) | Commented Out | Remove from [urls.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/urls.py). Code cleanup necessary. |
| 2 | `grades_report/` | `grades_report` (legacy views) | Commented Out | Verify if deprecated completely; if so, delete the corresponding view logic. |
| 3 | `entergrades/` | `entergrades` | Commented Out | Remove obsolete paths. Use singular entry points. |

### 5C - API Compliance

*   **Uses `@api_view` or `APIView`**: `WARN` - Uses `APIView` sub-classes mostly, but fails to adopt specific generics like `CreateAPIView`.
*   **Uses `permission_classes`**: `CRITICAL` - Permissions exist via scattered decorators/checks, often relying on session-based `request.user` vs DRF standard `Token/JWT` auth.
*   **Uses `authentication_classes`**: `WARN` - Relies heavily on legacy session mechanisms instead of strict DRF classes.
*   **Uses DRF Response**: `OK` - Utilizing `from rest_framework.response import Response`.
*   **Uses serializers for input**: `CRITICAL` - Scarcely used. Mostly `request.data.get('key')` overrides.
*   **Uses serializers for output**: `CRITICAL` - Extremely custom dict rebuilding across responses rather than relying on `Serializer.data`.
*   **Consistent error format**: `CRITICAL` - No custom exception handler. Varied `status=500/400` bodies string literals returned randomly.
*   **Pagination present**: `NON-STANDARD` - Very rarely applied generically; large record sets pull everything at once.
*   **API versioning**: `NON-STANDARD` - Lacking namespaced routing e.g., `/api/v1/examination/...`
*   **URL naming consistency**: `WARN` - Mixed `camelCase` and `snake_case` e.g., `submitGrades/` vs `upload_grades/` or `generate-result/`.

### 5D - Legacy Views

| No. | Function | URL | Needs API |
| :--- | :--- | :--- | :--- |
| 1 | `exam` | `/` | YES - requires explicit dashboard summary API |
| 2 | `browse_announcements` | N/A - nested internal usage | NO - Should become DB Selector |
| 3 | `authenticategrades` | `authenticategrades/` | YES - needs RESTful token/workflow verification mapping |
| 4 | `download_excel` | `download_excel/` | YES - requires refactoring to stream response correctly or serve signed URLs |
| 5 | `announcement` | `announcement/` | YES - needs API controller logic matching React standard |
| 6 | `verifyGradesDean` | `verifyGradesDean/` | YES - wrap as workflow update action mapped to `/api/grades/{id}/verify-dean` |
