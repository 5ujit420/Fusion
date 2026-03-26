# Visitor Hostel Module — Refactoring Implementation Plan

## Goal
Refactor the `visitor_hostel` module to resolve all 22 structural violations and 8 redundancies from the audit report. No logic changes — only relocation, consolidation, and structural improvements.

## Fix Mapping

| Audit ID | Problem | Fix Strategy | Target File |
|---|---|---|---|
| V-01 | Fat dashboard view (72 lines) | Extract to `services.build_dashboard_context()` | [services.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/visitor_hostel/services.py), [views.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/visitor_hostel/views.py) |
| V-02 | `User.objects.all()` in dashboard view | Move to `selectors.get_all_intenders()` | [selectors.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/visitor_hostel/selectors.py), [views.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/visitor_hostel/views.py) |
| V-03 | `User.objects.all()` in get_booking_form | Reuse `selectors.get_all_intenders()` | [views.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/visitor_hostel/views.py) |
| V-04 | `User.objects.get()` in request_booking | Move to `selectors.get_user_by_id()` | [selectors.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/visitor_hostel/selectors.py), [views.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/visitor_hostel/views.py) |
| V-05 | No input validation in legacy POST views | Validate via existing DRF serializers | [views.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/visitor_hostel/views.py) |
| V-06 | No role checks on legacy views | Add `role_required()` decorator | [views.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/visitor_hostel/views.py) |
| V-07 | No user-facing error feedback | Add Django `messages.error()` | [views.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/visitor_hostel/views.py) |
| V-08 | Bare `except Exception` in API views | Catch specific exceptions, generic error responses | [api/views.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/visitor_hostel/api/views.py) |
| V-09 | CancelBookingRequestView missing serializer | Create `CancelBookingRequestInputSerializer` | [api/serializers.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/visitor_hostel/api/serializers.py), [api/views.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/visitor_hostel/api/views.py) |
| V-10 | EditRoomStatusView missing serializer | Create `EditRoomStatusInputSerializer` | [api/serializers.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/visitor_hostel/api/serializers.py), [api/views.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/visitor_hostel/api/views.py) |
| V-11 | Legacy tuple choices | Migrate to `models.TextChoices` | [models.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/visitor_hostel/models.py) |
| V-12 | Dead [forms.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/visitor_hostel/forms.py) | Delete file | [forms.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/visitor_hostel/forms.py) |
| V-13 | Wildcard import in forms.py | Delete file (same as V-12) | [forms.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/visitor_hostel/forms.py) |
| V-14 | Cross-module coupling (notification import) | Wrap in `_send_notification()` helper | [services.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/visitor_hostel/services.py) |
| V-15 | N+1 in [calculate_mess_bill()](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/visitor_hostel/services.py#311-330) | Hoist meals query outside visitor loop | [services.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/visitor_hostel/services.py) |
| V-16 | O(n×m) in [get_available_rooms()](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/visitor_hostel/selectors.py#248-257) | Use `values_list` instead of nested Python loop | [selectors.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/visitor_hostel/selectors.py) |
| V-17 | Missing prefetch guard | Document requirement, add defensive prefetch | [services.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/visitor_hostel/services.py) |
| V-18 | `bd.category` (non-existent field) in confirm_booking | Fix to `bd.visitor_category` | [services.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/visitor_hostel/services.py) |
| V-19 | Fragile `hds[1]` index in get_incharge_user | Default to `hds.first()` | [selectors.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/visitor_hostel/selectors.py) |
| V-20 | Hard-coded wrong media path | Fix to use `VhImage/` subdirectory | [services.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/visitor_hostel/services.py) |
| V-21 | Inconsistent URL `bill_between_date_range/` | Rename to `bill-between-date-range/` | [urls.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/visitor_hostel/urls.py) |
| V-22 | Missing [__init__.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/visitor_hostel/api/__init__.py) check | Verify (already exists) | N/A |
| R-01 | Dashboard logic duplicated | Both views use `services.build_dashboard_context()` | [services.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/visitor_hostel/services.py), [views.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/visitor_hostel/views.py), [api/views.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/visitor_hostel/api/views.py) |
| R-02 | Booking+visitor creation duplicated | Create `services.create_booking_with_visitor()` | [services.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/visitor_hostel/services.py), [views.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/visitor_hostel/views.py), [api/views.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/visitor_hostel/api/views.py) |
| R-03 | Update booking input duplication | Add serializer validation to legacy view | [views.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/visitor_hostel/views.py) |
| R-04 | 11 legacy views duplicate API views | Add deprecation warnings | [views.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/visitor_hostel/views.py) |
| R-05 | Selector pairs differ only by user filter | Create `_get_bookings()` parametric builder | [selectors.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/visitor_hostel/selectors.py) |
| R-06 | Duplicate cancel-requested selectors | Merge into one with `future_only` param | [selectors.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/visitor_hostel/selectors.py) |
| R-07 | forms.py duplicates serializers | Delete forms.py | [forms.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/visitor_hostel/forms.py) |
| R-08 | Status update pattern duplicated 4× | Extract `_update_booking_status()` helper | [services.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/visitor_hostel/services.py) |
| Extra | [get_inactive_bookings](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/visitor_hostel/selectors.py#218-223) has "Cancelled" typo | Fix to "Canceled" | [selectors.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/visitor_hostel/selectors.py) |

---

## Proposed Changes

### Models
#### [MODIFY] [models.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/visitor_hostel/models.py)
- Replace 6 tuple-based choice constants with `TextChoices` enums: `VisitorCategory`, `RoomType`, `RoomFloor`, [RoomStatus](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/visitor_hostel/api/views.py#356-371), `BookingStatus`, `BillSettledBy`
- Update model field `choices=` kwargs to use enum `.choices`
- Keep `ROOM_RATES`, `MEAL_RATES`, `ROOM_BILL_BASE` constants unchanged
- Keep all 7 model schemas unchanged

---

### Selectors
#### [MODIFY] [selectors.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/visitor_hostel/selectors.py)
- Add `_get_bookings()` parametric base query builder (R-05)
- Refactor all ~15 booking selector functions to use it
- Add `get_all_intenders()` → `User.objects.all()` (V-02, V-03)
- Add `get_user_by_id(user_id)` (V-04)
- Fix [get_incharge_user()](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/visitor_hostel/selectors.py#362-372) to use `.first()` (V-19)
- Optimize [get_available_rooms()](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/visitor_hostel/selectors.py#248-257) with `values_list` (V-16)
- Merge duplicate cancel-requested selectors with `future_only` param (R-06)
- Fix [get_inactive_bookings](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/visitor_hostel/selectors.py#218-223) typo "Cancelled" → "Canceled"

---

### Services
#### [MODIFY] [services.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/visitor_hostel/services.py)
- Add `build_dashboard_context(user)` consolidating dashboard logic (V-01, R-01)
- Add `create_booking_with_visitor()` (R-02)
- Extract `_update_booking_status()` helper (R-08)
- Fix [confirm_booking()](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/visitor_hostel/views.py#190-205): `bd.category` → `bd.visitor_category` (V-18)
- Fix [calculate_mess_bill()](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/visitor_hostel/services.py#311-330): hoist query, remove N+1 (V-15)
- Fix [handle_booking_attachment()](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/visitor_hostel/services.py#113-131): correct media path (V-20)
- Wrap notification calls in `_send_notification()` (V-14)

---

### API Serializers
#### [MODIFY] [serializers.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/visitor_hostel/api/serializers.py)
- Add `CancelBookingRequestInputSerializer` (V-09)
- Add `EditRoomStatusInputSerializer` with choice validation (V-10)

---

### API Views
#### [MODIFY] [views.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/visitor_hostel/api/views.py)
- Use `services.build_dashboard_context()` in DashboardView (R-01)
- Use new serializers for CancelBookingRequest / EditRoomStatus (V-09, V-10)
- Replace bare `except Exception` with specific exceptions (V-08)
- Use `create_booking_with_visitor()` in RequestBookingView (R-02)

---

### Legacy Views
#### [MODIFY] [views.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/visitor_hostel/views.py)
- Add `role_required()` decorator, apply to 10 staff-only views (V-06)
- Use `services.build_dashboard_context()` in dashboard (V-01)
- Replace `User.objects` calls with selectors (V-02, V-03, V-04)
- Add input validation via DRF serializers to POST views (V-05)
- Add `messages.error()` feedback in except blocks (V-07)
- Use `create_booking_with_visitor()` (R-02)
- Add deprecation warnings to redundant views (R-04)

---

### URLs
#### [MODIFY] [urls.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/visitor_hostel/urls.py)
- Rename `bill_between_date_range/` → `bill-between-date-range/` (V-21)

---

### Cleanup
#### [DELETE] [forms.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/visitor_hostel/forms.py)
- Remove unused file (V-12, V-13, R-07)

---

### Tests
#### [MODIFY] [test_module.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/visitor_hostel/tests/test_module.py)
- Update for refactored function signatures (e.g., [get_cancel_requested_bookings_for_intender](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/visitor_hostel/selectors.py#104-110) with `future_only`)
- Add tests for: `build_dashboard_context`, `create_booking_with_visitor`, `_update_booking_status`, new serializers, role checks
- Verify bill calculation fixes

---

## Verification Plan

### Automated Tests
Existing tests are at [applications/visitor_hostel/tests/test_module.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/visitor_hostel/tests/test_module.py) (542 LOC, ~40 test methods).

**Command to run tests:**
```
cd c:\Users\sujit\OneDrive\Documents\Fusion_new\Fusion\FusionIIIT
python manage.py test applications.visitor_hostel.tests.test_module --verbosity=2
```

Tests cover: selector functions, service functions (CRUD, billing, inventory), serializer validation, API integration (auth, permissions, endpoints), and model constants.

After refactoring, all existing tests must pass, plus new tests for added functions.

### Manual Verification
- Verify [forms.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/visitor_hostel/forms.py) is deleted and no import errors occur
- Verify Django `makemigrations` shows no unintended schema changes (TextChoices migration is cosmetic only)
