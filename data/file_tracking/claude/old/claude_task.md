# Filetracking Module Refactoring

## Phase 1: Core Layer Files
- [x] Update [models.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/models.py) — add `MAX_FILE_SIZE_BYTES` constant (V-39)
- [x] Create [selectors.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/selectors.py) — extract all DB queries (V-02, R-05, R-06, R-07)
- [x] Create [services.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/services.py) — extract all business logic (V-01, V-04–V-11, V-41, R-01, R-02, R-04, R-08)

## Phase 2: API Layer
- [x] Rewrite [api/serializers.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/api/serializers.py) — explicit fields + input validators (V-25, V-26, V-37, V-38)
- [x] Rewrite [api/views.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/api/views.py) — thin views, fix security/bugs (V-12–V-21, V-27, V-28, V-32–V-34)
- [x] Rewrite [api/urls.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/api/urls.py) — migrate to `path()`
- [x] Rewrite root [views.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/notification/views.py) — thin views calling services (V-04–V-11, V-22–V-24, V-29–V-31, V-35, V-36)
- [x] Rewrite root [urls.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/urls.py) — migrate to `path()`
- [x] Update [utils.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/utils.py) — delegates to selectors (R-03)
- [x] Update [decorators.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/decorators.py) — fix bare except (V-31), use selectors
- [x] Rewrite [sdk/methods.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/sdk/methods.py) — thin wrapper delegating to services/selectors (V-41)

## Phase 3: Tests
- [x] Create [tests/__init__.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/complaint_system/tests/__init__.py)
- [x] Create [tests/test_module.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/tests/test_module.py) (V-03) — 45+ tests

## Phase 4: Cleanup
- [x] Delete old [tests.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/tests.py) placeholder
- [x] Create walkthrough / change log artifact
