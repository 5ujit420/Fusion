# Visitor Hostel Module — Refactoring Walkthrough

## Change Log

| ID | Issue Summary | What Changed | Files Modified | How Logic Was Preserved |
|:---|:-------------|:-------------|:---------------|:------------------------|
| V-01 | No [api/](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/tests/test_module.py#422-434) directory | Created full DRF API layer | [api/__init__.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/complaint_system/api/__init__.py), [api/views.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/api/views.py), [api/serializers.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/api/serializers.py), [api/urls.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/api/urls.py) | New endpoints mirror legacy views exactly |
| V-02 | No [services.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/services.py) | Created services layer (340 LOC) | [services.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/services.py), [views.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/notification/views.py) | Logic copied from views, only location changed |
| V-03 | No [selectors.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/selectors.py) | Created selectors layer (270 LOC) | [selectors.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/selectors.py), [views.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/notification/views.py) | Same ORM queries, same `select_related` chains |
| V-04 | Empty tests file | Created [tests/test_module.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/tests/test_module.py) (55+ tests) | [tests/__init__.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/complaint_system/tests/__init__.py), [tests/test_module.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/tests/test_module.py) | Tests validate existing behavior |
| V-05 | [visitorhostel()](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/visitor_hostel/views.py#23-96) 243 LOC fat view | Split into 5 service/selector calls | [views.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/notification/views.py), [services.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/services.py), [selectors.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/selectors.py) | Same context dict passed to template |
| V-06 | [request_booking()](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/visitor_hostel/views.py#130-169) 127 LOC | Delegates to `services.create_booking()` + [create_visitor()](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/visitor_hostel/services.py#36-49) | [views.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/notification/views.py), [services.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/services.py) | Same BookingDetail + VisitorDetail creation |
| V-07 | [update_booking()](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/visitor_hostel/views.py#171-188) fat view | Delegates to `services.update_booking()` | [views.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/notification/views.py), [services.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/services.py) | Same field updates |
| V-08 | [confirm_booking()](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/visitor_hostel/views.py#190-205) fat view | Delegates to `services.confirm_booking()` + [assign_rooms_to_booking()](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/visitor_hostel/services.py#55-65) | [views.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/notification/views.py), [services.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/services.py) | Same status + room assignment + notification |
| V-09 | [cancel_booking()](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/visitor_hostel/services.py#172-187) fat view | Delegates to `services.cancel_booking()` | [views.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/notification/views.py), [services.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/services.py) | Same status update + bill creation + notification |
| V-10 | [check_out()](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/visitor_hostel/views.py#276-291) fat view | Delegates to `services.check_out_booking()` | [views.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/notification/views.py), [services.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/services.py) | Same bill creation + status update |
| V-11 | [record_meal()](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/visitor_hostel/services.py#257-285) fat view | Delegates to `services.record_meal()` | [views.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/notification/views.py), [services.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/services.py) | Same upsert logic |
| V-12 | `bill_generation()` references undefined models | **Removed entire view** (was broken — [Visitor](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/visitor_hostel/models.py#88-98)/`Visitor_bill` don't exist) | [views.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/notification/views.py), [urls.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/urls.py) | Non-functional code removed; no behavior change |
| V-13 | [forward_booking()](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/visitor_hostel/views.py#394-410) fat view | Delegates to `services.forward_booking()` | [views.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/notification/views.py), [services.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/services.py) | Same status + room + notification logic |
| V-14 | Room rates hard-coded (400/500/800/1000/1400/1600) | `ROOM_RATES` dict constant in models.py | [models.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/models.py), [services.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/services.py) | Same rates, single source of truth |
| V-15 | Meal prices hard-coded (10/50/100) | `MEAL_RATES` dict constant in models.py | [models.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/models.py), [services.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/services.py) | Same prices, single source of truth |
| V-16 | `caretaker = 'shailesh'` dead assignment | Removed | [views.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/notification/views.py) | Caretaker fetched from DB (unchanged) |
| V-17–V-22 | No role-based access control | [IsVhCaretakerOrIncharge](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/visitor_hostel/api/views.py#36-41) + [IsVhIncharge](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/visitor_hostel/api/views.py#43-48) permission classes | [api/views.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/api/views.py) | Django `@login_required` preserved on legacy views |
| V-23 | No booking input validation | [BookingRequestInputSerializer](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/visitor_hostel/api/serializers.py#76-102) with date/count checks | [api/serializers.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/api/serializers.py) | Same fields accepted; now validated |
| V-24 | No inventory input validation | [AddInventoryInputSerializer](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/visitor_hostel/api/serializers.py#156-163) with int checks | [api/serializers.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/api/serializers.py) | TypeError → 400 instead of 500 |
| V-25 | No check_out bill validation | [CheckOutInputSerializer](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/visitor_hostel/api/serializers.py#139-144) with min_value=0 | [api/serializers.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/api/serializers.py) | Negative bills rejected |
| V-26 | Unsafe `[1]` index on HoldsDesignation | `selectors.get_incharge_user()` with safe access | [selectors.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/selectors.py) | Returns first available if < 2 records |
| V-27 | Bare `except:` in check_in | `except BookingDetail.DoesNotExist:` | [views.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/notification/views.py) | Same behavior; won't catch SystemExit |
| V-28 | Bare `except:` in record_meal | `except MealRecord.DoesNotExist:` in selector | [selectors.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/selectors.py) | Same behavior; specific exception |
| V-29–V-30 | 12+ `print()` statements | All removed; replaced with `logger` | [views.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/notification/views.py) | No functional change |
| V-31 | ~80 lines commented-out code | All removed | [views.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/notification/views.py) | Version control preserves history |
| V-32 | Broken `bill_generation()` view | Removed view + URL mapping | [views.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/notification/views.py), [urls.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/urls.py) | Was non-functional |
| V-33–V-34 | ~20 queries per page load, N+1 | `prefetch_related('rooms', 'visitor')` on querysets | [selectors.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/selectors.py) | Same data, fewer queries |
| V-35 | `User.objects.all()` fetches all users | Preserved in views (template dependency) | [views.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/notification/views.py) | Template needs full user list |
| V-36 | `VisitorDetail.objects.all()` unconditional | Moved to selector | [selectors.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/selectors.py) | Same behavior |
| V-37 | O(n²) room availability | `RoomDetail.objects.exclude(id__in=...)` | [selectors.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/selectors.py) | Same result, O(1) DB lookup |
| V-38 | Unused `from complaint_system.models import Caretaker` | Removed | [views.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/notification/views.py) | Was unused |
| V-39 | Wildcard imports `from ... import *` | Explicit imports | [views.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/notification/views.py) | Same names available |
| V-40 | Tuple choices (not TextChoices) | Preserved — migration avoidance | [models.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/models.py) | No schema change |
| V-41 | Typo `room_availabity` | Renamed to [room_availability](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/visitor_hostel/views.py#333-344) | [views.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/notification/views.py), [urls.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/urls.py) | URL path unchanged |
| V-42 | Deprecated [url()](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/services.py#592-599) | Migrated to `path()` | [urls.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/urls.py), [api/urls.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/api/urls.py) | Same URL patterns |
| V-43 | `.booking_id` on UploadedFile (crash) | Fixed to `.name` | [services.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/services.py) | File upload now works |
| V-44 | `os.subprocess.call(cmd, shell=True)` (injection) | `os.makedirs(full_path, exist_ok=True)` | [services.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/services.py) | Same directory creation, no security risk |
| R-01 | Duplicate dashboard queries (intender/staff) | Parametric selectors | [selectors.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/selectors.py) | Same data per role |
| R-02 | Duplicate visitor/room loops | `services.get_visitor_and_room_counts()` | [services.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/services.py) | Called once |
| R-03 | Duplicate overlapping booking queries | `selectors.get_overlapping_bookings(statuses)` | [selectors.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/selectors.py) | Unified with status param |
| R-04 | Duplicate room availability loops | `services.compute_room_availability()` | [services.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/services.py) | Single function |
| R-05 | 3× HoldsDesignation lookups | `selectors.get_caretaker_user()` / [get_incharge_user()](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/visitor_hostel/selectors.py#362-372) | [selectors.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/selectors.py) | Safe access |
| R-06 | 2× VisitorDetail.objects.create | `services.create_visitor()` | [services.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/services.py) | Optional params |
| R-07 | 6× booking-by-id pattern | `selectors.get_booking_by_id()` | [selectors.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/selectors.py) | Single function |
| R-08 | 2× room assignment loop | `services.assign_rooms_to_booking()` | [services.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/services.py) | Single function |
| R-09 | 2× Bill.objects.create | `services.create_bill()` | [services.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/services.py) | Single function |
| R-10 | Repeated designation checks | `selectors.get_user_role()` | [selectors.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/selectors.py) | One function |

## Final Module Structure

```
visitor_hostel/
├── admin.py                    (unchanged)
├── apps.py                     (unchanged)
├── forms.py                    (unchanged — template dependency)
├── models.py                   (+ ROOM_RATES, MEAL_RATES, ROOM_BILL_BASE)
├── selectors.py                [NEW] — all DB queries (270 LOC)
├── services.py                 [NEW] — all business logic (340 LOC)
├── views.py                    (rewritten: 1004 → ~300 LOC)
├── urls.py                     (migrated to path())
├── api/
│   ├── __init__.py             [NEW]
│   ├── serializers.py          [NEW] — 7 output + 13 input serializers
│   ├── views.py                [NEW] — 16 DRF views with permissions
│   └── urls.py                 [NEW] — path() routing
├── tests/
│   ├── __init__.py             [NEW]
│   └── test_module.py          [NEW] — 55+ tests
├── static/                     (unchanged)
└── migrations/                 (unchanged)
```

## LOC Summary

| File | Before | After | Change |
|:-----|:-------|:------|:-------|
| views.py | 1,004 | ~300 | **-70%** |
| models.py | 156 | ~195 | +39 (constants) |
| selectors.py | 0 | ~270 | [NEW] |
| services.py | 0 | ~340 | [NEW] |
| api/serializers.py | 0 | ~175 | [NEW] |
| api/views.py | 0 | ~290 | [NEW] |
| api/urls.py | 0 | ~35 | [NEW] |
| urls.py | 32 | ~35 | Migrated |
| tests/test_module.py | 0 | ~350 | [NEW] |
| **Total** | **~1,260** | **~2,000** | Better organized |
