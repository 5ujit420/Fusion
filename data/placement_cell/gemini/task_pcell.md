# pcell Refactoring Task List

## 1. Setup Architecture (SA-1, SA-2, SA-3)
- [x] Create [services.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/services.py)
- [x] Create [selectors.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/selectors.py)
- [x] Create [api/views.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/api/views.py)
- [x] Create [api/urls.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/api/urls.py)

## 2. Refactor Massive [views.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/globals/views.py) (SA-4, SA-5, SA-9)
- [x] Extract DB Queries into [selectors.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/selectors.py) (RR-3)
- [x] Extract Form/POST Logic into [services.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/services.py)
- [x] Migrate Endpoints to [api/views.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/api/views.py)
- [x] Create missing DRF `InputSerializers`

## 3. Serializers & Models (SA-6, SA-10)
- [x] Remove [create()](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/placement_cell/services.py#68-77) logic from [HasSerializer](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/placement_cell/api/serializers.py#14-18)
- [x] Expose standard Serializers for the remaining payload definitions

## 4. Routing & Security (SA-7, SA-8, RR-2)
- [x] Implement explicit object-level permission check for deletes
- [x] Delete [urls.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/Fusion/urls.py) legacy routes
- [x] Wire [api/urls.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/api/urls.py) correctly

## 5. Testing
- [x] Write [tests/test_module.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/tests/test_module.py)
- [x] Execute `manage.py test` to verify architecture

## 6. Output Generation
- [x] Create Change Log
- [x] Assemble all module files into a single output document
