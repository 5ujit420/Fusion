# Placement Cell Refactoring Implementation Plan

## Goal Description
Perform a complete architectural refactoring of the `placement_cell` (pcell) module to comply strictly with the target DRF-driven separated-layer architecture. We will break down the massive 5,000+ line [views.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/views.py) file, extracting all business logic into [services.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/services.py), isolating database accesses into [selectors.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/selectors.py), moving input validation into DRF [serializers.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/api/serializers.py), and converting routing exclusively to API endpoints inside [api/urls.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/api/urls.py) attached to thin [api/views.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/api/views.py).

## Proposed Changes

### Configuration
#### [MODIFY] [urls.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/placement_cell/urls.py)
- Route root [placement/](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/placement_cell/views.py#2904-3187) traffic directly into [api/urls.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/api/urls.py).
- Delete all local legacy UI-coupled routes.

---

### Core Separations
#### [NEW] [services.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/placement_cell/services.py)
- **SA-1 / SA-4 / SA-5 / RR-1**: Implement all pure business behavior dynamically executed inside legacy [views.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/views.py).
- Functions to create: `calculate_statistics()`, `save_placement_record()`, `create_placement_schedule()`, [delete_invitation()](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/placement_cell/views.py#3189-3249), `save_placement_visit()`.

#### [NEW] [selectors.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/placement_cell/selectors.py)
- **SA-2 / RR-3**: Extract the 600+ inline `.objects.` API accesses into rigidly defined accessor functions.
- Functions to create: [get_reference_list()](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/placement_cell/views.py#2195-2209), `get_placement_record()`, `get_all_invitations()`, `get_user_profile()`.

---

### API Boundary
#### [NEW] [api/urls.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/placement_cell/api/urls.py)
- **SA-3 / SA-7**: Convert all 17 endpoint locations into strict REST-compliant routes mapped directly to DRF APIViews.

#### [NEW] [api/views.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/placement_cell/api/views.py)
- **SA-9 / RR-2**: Implement explicit class-based DRF Views holding permission logic (e.g., `IsOwnerOrSuperuser` for [delete_invite_status](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/placement_cell/views.py#4531-4591)).
- Map all `POST`/`GET` functions explicitly to DRF operations.

#### [MODIFY] [api/serializers.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/placement_cell/api/serializers.py)
- **SA-6**: Strip business logic block [create()](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/placement_cell/api/serializers.py#22-30) from [HasSerializer](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/placement_cell/api/serializers.py#15-30).
- Expose InputSerializers for payload validation representing `RecordInputSerializer`, `ScheduleInputSerializer`, and `VisitInputSerializer`.

---

### Legacy Cleanup
#### [DELETE] [views.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/placement_cell/views.py)
- Completely deprecate the massive legacy file to guarantee zero legacy structural reliance.

---

## Verification Plan
### Automated Tests
- Run `manage.py check` to ensure total DRF router compilation success.
- Execute unit testing `python manage.py test applications.placement_cell` using the `--keepdb` local SQLite mocking strategy.

### Manual Verification
- Manually review the output consolidated file to ensure exact function parity with the audit.
