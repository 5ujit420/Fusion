# Examination Module Refactoring Plan

## Step 1 - Extract Audit Issues
- SA-01: Missing Folder Structure (`services.py`, `selectors.py`)
- SA-02: Mixed Responsibilities in `submitEntergradesStoring`
- SA-03: Fat View `upload_grades`
- SA-04: Fat View `validateDeanSubmit`
- SA-05: Fat View `generate_pdf`
- SA-06: Fat View `generate_result`
- SA-07: Legacy Code Leak in `calculate_cpi_for_student`
- SA-08: Fat View `download_template`
- SA-09: Logic in Serializer `UploadGradesAPI`
- SA-10: Fat View `ModerateStudentGradesAPI`
- SA-11: Fat View `GenerateResultAPI`
- SA-12: Fat View `UploadGradesProfAPI`
- SA-13: Cross-Module Tight Coupling
- SA-14, SA-15: Hard-coded Values in [models.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/models.py)
- SA-16: Missing Input Validation `request.data.get('X')`
- RR-01: Redundant `submitGrades` vs `SubmitGradesView`
- RR-02: Redundant `upload_grades` vs `UploadGradesAPI`
- RR-03: Redundant `UploadGradesAPI` vs `UploadGradesProfAPI`
- RR-04: Redundant `generate_transcript`
- RR-05: Redundant queries in result generation
- RR-06: Redundant PDF generation logic
- RR-07: Redundant `updateEntergrades`
- RR-08: Redundant `validateDean`

## Step 2 - Map Issues to Fix Plan
| Audit ID | Problem | Fix Strategy | Target File |
|---|---|---|---|
| SA-01 | Missing structure | Create files | `services.py`, `selectors.py` |
| SA-14, SA-15 | Models text choices | Use `TextChoices` | [models.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/models.py) |
| SA-16 | Missing Validation | Create serializers | [api/serializers.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/api/serializers.py) |
| SA-07, RR-05 | CPI math in view | Move math | `services.py` |
| SA-06, SA-11 | Results computation | Move computation | `services.py` |
| SA-03, SA-09, SA-12, RR-02, RR-03 | Upload grades logic | Unify upload | `services.py` |
| SA-02, RR-01 | Submit grades | Extract submit rules | `services.py` |
| SA-04, RR-08 | Dean workflow | Extract dean checks | `services.py` |
| SA-05, RR-06 | PDF generation | Move to service | `services.py` |
| RR-07 | Update enter grades | Unify logic | `services.py` |

## Step 3 & 4 - Execution Order
1. [models.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/models.py): Implement TextChoices and update hardcoded fields.
2. `selectors.py`: Abstract cross-module imports and complex queries.
3. `services.py`: Unify and implement business logic for computation, pdf generation, dean validation, grade submissions, etc.
4. [api/serializers.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/api/serializers.py): Add validation schemas for all inputs.
5. [api/urls.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/api/urls.py) and [api/views.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/api/views.py): Deplete all logic, using serializers + selectors + services.
6. [urls.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/urls.py) and [views.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/views.py): Do the same for legacy web views.
7. `tests/test_module.py`: Write comprehensive integration tests.
8. Create final changelog artifact.
