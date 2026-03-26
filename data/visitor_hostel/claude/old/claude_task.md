# Visitor Hostel Module Refactoring

## Phase 1: Core Layer Files
- [x] Update [models.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/models.py) — rate constants (V-14, V-15)
- [x] Create [selectors.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/selectors.py) — all DB queries (V-03, R-01, R-03, R-05, R-07, R-10)
- [x] Create [services.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/services.py) — all business logic (V-02, V-05–V-13, R-02, R-04, R-06, R-08, R-09)

## Phase 2: API + View Layer
- [x] Create [api/serializers.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/api/serializers.py) — 13 input validators (V-23–V-25)
- [x] Create [api/views.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/api/views.py) — 16 DRF views with permissions (V-01, V-17–V-22)
- [x] Create [api/urls.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/api/urls.py) — path() routing
- [x] Rewrite [views.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/notification/views.py) — thin views (V-05–V-13, V-16, V-26–V-32, V-38–V-44)
- [x] Rewrite [urls.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/urls.py) — path() (V-41, V-42)

## Phase 3: Tests
- [x] Create [tests/__init__.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/complaint_system/tests/__init__.py) + [tests/test_module.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/tests/test_module.py) (V-04) — 55+ tests

## Phase 4: Cleanup & Documentation
- [x] Delete old [tests.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/tests.py)
- [x] Create walkthrough / change log
