# Examination Module Refactoring — Task Tracker

## Phase 1: Foundation Layer
- [x] Create [constants.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/constants.py) (V13, V30, V31)
- [x] Create [selectors.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/selectors.py) (V02, R09, R10, R11)
- [x] Create [services.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/services.py) (V01, V12)
- [x] Create [permissions.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/permissions.py) (V18)

## Phase 2: Models & Admin
- [x] Rename models to PascalCase with `db_table` meta (V35)
- [x] Update [admin.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/admin.py) with renamed models
- [x] Fix [apps.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/apps.py) default_auto_field

## Phase 3: Service Extraction
- [x] Extract SPI/CPI helpers to [services.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/services.py) (V12)
- [x] Extract CSV upload logic to [services.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/services.py) (V04, V05)
- [x] Extract Excel generation to [services.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/services.py) (V06)
- [x] Extract PDF generation to [services.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/services.py) (V07, V08)
- [x] Consolidate student result PDF (R06)
- [x] Extract grade moderation to [services.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/services.py)
- [x] Fix N+1 queries (V32, V33, V34)
- [x] Replace raw SQL with ORM (V39)

## Phase 4: Serializers
- [x] Fix [AuthenticationSerializer](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/api/serializers.py#32-37) model ref (V23)
- [x] Create proper input/output serializers (V24)

## Phase 5: API Views Refactoring
- [x] Thin all fat views — delegate to services/selectors
- [x] Replace `request.data.get("Role")` with permission classes (V18)
- [x] Fix error handling (V20, V21, V22)
- [x] Add file size limits (V19)
- [x] Split `GeneratePDFAPI.post()` dispatcher (V38)

## Phase 6: Legacy Cleanup
- [x] Remove all legacy views duplicated by API (R01–R05, R07, R10, R12)
- [x] Remove dead code and unreachable lines (V25–V29)
- [x] Remove [print()](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/tests/test_module.py#241-259) statements (V41)
- [x] Fix deprecated APIs: [url()](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/tests/test_module.py#276-285) → `path()` (V40)
- [x] Standardize URLs to kebab-case (V36)
- [x] Retain legacy views that serve templates (not duplicated)

## Phase 7: URL Cleanup
- [x] Rewrite [urls.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/urls.py) with only non-API template-serving routes
- [x] Rewrite [api/urls.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/api/urls.py) with `path()` and kebab-case

## Phase 8: Tests
- [x] Create [tests/__init__.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/tests/__init__.py)
- [x] Create [tests/test_module.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/tests/test_module.py) with comprehensive tests
- [x] Delete old [tests.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/examination/tests.py)

## Phase 9: Verification
- [x] Verify all SA-# fixed
- [x] Verify all RR-# resolved
- [x] Create walkthrough document
