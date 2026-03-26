# Complaint System Module Refactoring

## Phase 1: Create Core Layer Files
- [x] Create [models.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/complaint_system/models.py) — add TextChoices, `COMPLAINT_TYPE_DAYS`, `LOCATION_DESIGNATION_MAP` constants (V-29, V-30, R-07, R-08)
- [x] Create [selectors.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/complaint_system/selectors.py) — extract all DB queries (V-02, V-38)
- [x] Create [services.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/complaint_system/services.py) — extract all business logic (V-01, V-04–V-17, V-20, R-01–R-06)
- [x] Create [permissions.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/complaint_system/permissions.py) — custom DRF permission classes (V-26, V-27)

## Phase 2: Refactor API Layer
- [x] Rewrite [api/serializers.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/complaint_system/api/serializers.py) — consolidate from both root and api/ (V-21, V-22, V-23, V-24, V-25, R-09)
- [x] Rewrite [api/views.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/complaint_system/api/views.py) — thin views using services/selectors (V-04–V-19, V-28, V-31–V-37)
- [x] Rewrite [api/urls.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/complaint_system/api/urls.py) — clean routing (V-37)
- [x] Delete old root [views.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/notification/views.py), [serializers.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/complaint_system/serializers.py), [urls.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/complaint_system/urls.py), [tests.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/complaint_system/tests.py)

## Phase 3: Tests
- [x] Create [tests/__init__.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/complaint_system/tests/__init__.py)
- [x] Create [tests/test_module.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/complaint_system/tests/test_module.py) — service, selector, serializer, and API tests (V-03)

## Phase 4: Cleanup & Documentation
- [x] [admin.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/complaint_system/admin.py) — no changes needed (already clean)
- [x] [apps.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/complaint_system/apps.py) — no changes needed (already clean)
- [x] Create change log / walkthrough artifact
