# Structural Audit & Refactoring Plan: Visitor Hostel Module

## SECTION 1: MODULE SNAPSHOT

| Metric | Value | Measurement Method |
| :--- | :--- | :--- |
| **Total LOC (approx.)** | ~2200 | Counted lines across all [.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/manage.py) files in `visitor_hostel/` |
| **LOC in [views.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/views.py)** | 416 | Line count of [visitor_hostel/views.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/visitor_hostel/views.py) |
| **LOC in [api/views.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/api/views.py)** | 371 | Line count of [visitor_hostel/api/views.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/visitor_hostel/api/views.py) |
| **No. of service files** | 1 | Counted [services.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/services.py) |
| **No. of serializer classes** | 21 | Counted classes in [api/serializers.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/api/serializers.py) |
| **No. of models** | 7 | Counted Model classes in [models.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/models.py) |
| **Number of API endpoints** | 17 | Counted routes in [api/urls.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/api/urls.py) |
| **Number of DB queries in views** | 0 | Verified all `.objects` calls are properly contained in [selectors.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/selectors.py) |
| **No. of structural violations** | 4 | Identified based on strict DRF/backend architecture requirements |
| **No. of redundancy items** | 2 | Identified overlapping endpoints and UI artifacts |
| **[services.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/services.py) exists** | Y | Verified file presence and usage |
| **[selectors.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/selectors.py) exists** | Y | Verified file presence and usage |
| **`tests/` folder exists** | Y | Verified folder presence |
| **[api/](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/tests/test_module.py#422-434) folder exists** | Y | Verified folder presence |
| **Uses TextChoices** | N | [models.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/models.py) uses legacy tuples (e.g., `ROOM_TYPE`, `VISITOR_CATEGORY`) |
| **Overall Structural State** | Moderate | Core logic is properly decoupled into `services` and `selectors`, but legacy HTML views, URLs, and forms continue to create a dual-head burden. |

---

## SECTION 2: STRUCTURAL AUDIT

| ID | Category | File | Line Range | Description | Impact | Planned Fix | Detailed Fix Steps |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| SA-1 | Mixed Responsibilities | [views.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/views.py) | 1-416 | Root-level views mapping to HTML templates ([render](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/placement_cell/views.py#5390-5410), `HttpResponseRedirect`) violate the API-only Thin Views architectural rule. | HIGH | Delete file | Completely remove [views.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/views.py). All interactions must be solely driven by existing [api/views.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/api/views.py) endpoints which safely invoke the shared [services.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/services.py). |
| SA-2 | Missing Folder Structure | [urls.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/urls.py) | 1-38 | Root-level URLs map to deprecated HTML-rendering views and violate standard API routing conventions. | HIGH | Delete file | Delete the root-level [urls.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/urls.py). Rely solely on [api/urls.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/api/urls.py) for routing interactions. Remove inclusion from the main project router if it bypasses the [api/](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/tests/test_module.py#422-434) namespace. |
| SA-3 | Non-Standard Pattern | [forms.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/placement_cell/forms.py) | 1-42 | Django `forms.Form` logic is present. In an API-driven architecture, input validation belongs in DRF Serializers. | MEDIUM | Delete file | Delete [forms.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/placement_cell/forms.py) since all input validations have already been mirrored correctly into DRF serializers in [api/serializers.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/api/serializers.py). |
| SA-4 | Hard-coded Values | [models.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/models.py) | 16-81 | Business logic configuration variables and hard-coded rates (`ROOM_RATES`, `MEAL_RATES`, `ROOM_BILL_BASE`) are improperly stored in the models file. Legacy choice tuples are used instead of `TextChoices`. | LOW | Move to serializers | Migrate business logic dictionaries to [api/serializers.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/api/serializers.py). Optional: Upgrade model choice tuples to `TextChoices` if schema uncompromised. |

---

## SECTION 3: REDUNDANCY REGISTER

| ID | Type | Location 1 | Location 2 | Description | Redundant | Plan | Detailed Consolidation |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| RR-1 | Concept | [views.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/views.py) (L23-411) | [api/views.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/api/views.py) (L54-371) | Dual-head technical debt where every logical API endpoint has a mirrored HTML-rendering view. | [views.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/views.py) | Delete [views.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/views.py) | Eliminate the legacy HTML views. The Single Source of Truth for controllers will strictly be [api/views.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/api/views.py). |
| RR-2 | Validation | [forms.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/placement_cell/forms.py) (L1-42) | [api/serializers.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/api/serializers.py) (L76-186) | Django Forms duplicate validation logic that is securely handled by DRF `InputSerializers`. | [forms.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/placement_cell/forms.py) | Delete [forms.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/placement_cell/forms.py) | Purge the [forms.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/placement_cell/forms.py) file completely. Rely exclusively on DRF validation serializers. |

---

## SECTION 4: REFACTORING PLAN

| Ref IDs | Action | Target Files | Validation |
| :--- | :--- | :--- | :--- |
| SA-1, RR-1 | Delete legacy UI views | [views.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/views.py) | Run the test suite (`python manage.py test applications.visitor_hostel`) to ensure [services.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/services.py) and [selectors.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/selectors.py) continue functioning normally. |
| SA-2 | Delete root URLs | [urls.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/urls.py) | Manual check of main project [urls.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/urls.py) to ensure traffic delegates correctly strictly to `visitor_hostel/api/urls.py`. |
| SA-3, RR-2 | Delete forms | [forms.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/placement_cell/forms.py) | Run test suite to verify no imports crash due to missing forms module. API logic inherently uses DRF serializers. |
| SA-4 | Refactor Constants out of Models | [models.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/models.py), [services.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/services.py) | Move rate configurations to [services.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/services.py) explicitly where they are used. Run tests comparing bill output calculation logic. |

---

## SECTION 5: API AUDIT

### 5A - Active APIs

| No. | URL | Method | View | Auth | Role Check | Serializer | Status | Validation | Fix Plan |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | [api/](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/tests/test_module.py#422-434) | GET | [DashboardView](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/visitor_hostel/api/views.py#54-77) | Token | Yes (`IsAuthenticated`) | Output S. | OK | Handled by implicit [DashboardView](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/visitor_hostel/api/views.py#54-77) logic | None needed |
| 2 | `api/booking/request/` | POST | [RequestBookingView](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/visitor_hostel/api/views.py#83-117) | Token | Yes | [BookingRequestInput](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/visitor_hostel/api/serializers.py#76-102) | OK | Strict via Serializer | None needed |
| 3 | `api/booking/update/` | POST | [UpdateBookingView](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/visitor_hostel/api/views.py#119-137) | Token | Yes | [UpdateBookingInput](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/visitor_hostel/api/serializers.py#104-112) | OK | Strict via Serializer | None needed |
| 4 | `api/booking/confirm/` | POST | [ConfirmBookingView](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/visitor_hostel/api/views.py#139-154) | Token | Yes ([IsVhIncharge](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/visitor_hostel/api/views.py#43-48)) | [ConfirmBookingInput](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/visitor_hostel/api/serializers.py#114-118) | OK | Strict via Serializer | None needed |
| 5 | `api/booking/cancel/` | POST | [CancelBookingView](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/visitor_hostel/api/views.py#156-172) | Token | Yes ([IsVhCaretakerOrIncharge](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/visitor_hostel/api/views.py#36-41)) | [CancelBookingInput](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/visitor_hostel/api/serializers.py#120-124) | OK | Strict via Serializer | None needed |
| 6 | `api/booking/cancel-request/` | POST | [CancelBookingRequestView](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/visitor_hostel/api/views.py#174-186) | Token | Yes | None (manual `request.data.get`) | WARN | Mixed manual vs Serializer | Consider creating a basic InputSerializer to formalize the `{booking-id, remark}` parameters. |
| 7 | `api/booking/reject/` | POST | [RejectBookingView](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/visitor_hostel/api/views.py#188-200) | Token | Yes ([IsVhIncharge](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/visitor_hostel/api/views.py#43-48)) | [RejectBookingInput](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/visitor_hostel/api/serializers.py#126-129) | OK | Strict via Serializer | None needed |
| 8 | `api/visitor/check-in/` | POST | [CheckInView](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/visitor_hostel/api/views.py#202-219) | Token | Yes ([IsVhCaretakerOrIncharge](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/visitor_hostel/api/views.py#36-41)) | [CheckInInput](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/visitor_hostel/api/serializers.py#131-137) | OK | Strict via Serializer | None needed |
| 9 | `api/visitor/check-out/` | POST | [CheckOutView](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/visitor_hostel/api/views.py#221-235) | Token | Yes ([IsVhCaretakerOrIncharge](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/visitor_hostel/api/views.py#36-41)) | [CheckOutInput](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/visitor_hostel/api/serializers.py#139-144) | OK | Strict via Serializer | None needed |
| 10 | `api/meal/record/` | POST | [RecordMealView](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/visitor_hostel/api/views.py#237-254) | Token | Yes ([IsVhCaretakerOrIncharge](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/visitor_hostel/api/views.py#36-41)) | [RecordMealInput](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/visitor_hostel/api/serializers.py#146-154) | OK | Strict via Serializer | None needed |
| 11 | `api/booking/forward/` | POST | [ForwardBookingView](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/visitor_hostel/api/views.py#256-273) | Token | Yes ([IsVhCaretakerOrIncharge](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/visitor_hostel/api/views.py#36-41)) | [ForwardBookingInput](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/visitor_hostel/api/serializers.py#170-176) | OK | Strict via Serializer | None needed |
| 12 | `api/room/availability/` | POST | [RoomAvailabilityView](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/visitor_hostel/api/views.py#279-290) | Token | Yes | [RoomAvailabilityInput](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/visitor_hostel/api/serializers.py#178-181) | OK | Strict via Serializer | None needed |
| 13 | `api/inventory/add/` | POST | [AddInventoryView](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/visitor_hostel/api/views.py#296-313) | Token | Yes ([IsVhCaretakerOrIncharge](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/visitor_hostel/api/views.py#36-41)) | [AddInventoryInput](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/visitor_hostel/api/serializers.py#156-163) | OK | Strict via Serializer | None needed |
| 14 | `api/inventory/update/` | POST | [UpdateInventoryView](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/visitor_hostel/api/views.py#315-326) | Token | Yes ([IsVhCaretakerOrIncharge](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/visitor_hostel/api/views.py#36-41)) | [UpdateInventoryInput](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/visitor_hostel/api/serializers.py#165-168) | OK | Strict via Serializer | None needed |
| 15 | `api/bill/range/` | POST | [BillBetweenDatesView](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/visitor_hostel/api/views.py#332-350) | Token | Yes ([IsVhCaretakerOrIncharge](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/visitor_hostel/api/views.py#36-41)) | [BillDateRangeInput](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/visitor_hostel/api/serializers.py#183-186) | OK | Strict via Serializer | None needed |
| 16 | `api/room/status/` | POST | [EditRoomStatusView](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/visitor_hostel/api/views.py#356-371) | Token | Yes ([IsVhCaretakerOrIncharge](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/visitor_hostel/api/views.py#36-41)) | None (manual `request.data.get`) | WARN | Mixed manual vs Serializer | Create InputSerializer to standardize `room_number` and [room_status](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/visitor_hostel/views.py#379-392). |

### 5B - Inactive APIs
| No. | URL | View | Status | Action |
| :--- | :--- | :--- | :--- | :--- |
| 1 | All root URLs in `<module>/urls.py` | [views.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/views.py) views | NON-STANDARD | Delete immediately to enforce API usage exclusively. |

### 5C - API Compliance

*   **Uses @api_view or APIView:** Yes ([APIView](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/complaint_system/api/views.py#550-573) extensively used).
*   **Uses permission_classes:** Yes (e.g., `IsAuthenticated`, [IsVhCaretakerOrIncharge](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/visitor_hostel/api/views.py#36-41)).
*   **Uses authentication_classes:** Yes (`TokenAuthentication`).
*   **Uses DRF Response:** Yes.
*   **Uses serializers for input:** Partially (Missed in [CancelBookingRequestView](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/visitor_hostel/api/views.py#174-186) and [EditRoomStatusView](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/visitor_hostel/api/views.py#356-371)).
*   **Uses serializers for output:** Yes.
*   **Consistent error format:** Yes, standard HTTP 400 responses with `{error: str(e)}`.
*   **Pagination present:** No (can be added if data volume expands).
*   **API versioning:** No (Current structure is flat).
*   **URL naming consistency:** Yes, grouped by domain (`api/booking/`, `api/inventory/`).

### 5D - Legacy Views

| No. | Function | URL | Needs API |
| :--- | :--- | :--- | :--- |
| # | All remaining root views (e.g., [visitorhostel](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/visitor_hostel/views.py#23-96), [request_booking](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/visitor_hostel/views.py#130-169), etc.) | Root `/visitorhostel/` | ALREADY HAS API. Must be purged to relieve technical debt. |
