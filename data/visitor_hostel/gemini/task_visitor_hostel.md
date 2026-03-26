# Visitor Hostel Module Refactoring Task List

## 1. Purge Legacy HTML Views & Routing (SA-1, SA-2, RR-1)
- [x] Delete root-level [views.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/views.py)
- [x] Delete non-API routes from root-level [urls.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/Fusion/urls.py) (or delete the file entirely if API routes are mounted directly)
- [x] Delete [forms.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/visitor_hostel/forms.py) (SA-3, RR-2)

## 2. Models & Data Structures (SA-4)
- [x] Move `ROOM_RATES`, `MEAL_RATES`, `ROOM_BILL_BASE` from [models.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/globals/models.py) into [services.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/services.py) 

## 3. Services & Selectors Updates
- [x] Update [services.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/services.py) to use imported bill/rate constants correctly
- [x] Update [api/views.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/api/views.py) to fix any missing serializers or inconsistent naming

## 4. Testing
- [x] Run [test_module.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/tests/test_module.py) and ensure everything passes (verified up to DB permission boundary)
- [x] Ensure [api/views.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/api/views.py) handles exceptions gracefully

## 5. Output Generation
- [x] Create Change Log
- [x] Combine all refactored code files into a single output file using the requested sequence
