# Structural Audit & Refactoring Plan: [filetracking](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/views.py#26-90) Module

## 1. Executive Summary
The [filetracking](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/views.py#26-90) module has undergone substantial and successful refactoring. It currently features a robust [services.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/services.py) layer (business logic), a [selectors.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/selectors.py) layer (database queries), and a dedicated [api/](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/complaint_system/services.py#428-451) directory with thin DRF views and serializers. A comprehensive test suite is also present in [tests/test_module.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/tests/test_module.py).

However, an audit against the **Strict Target Architecture** reveals that the module currently operates in a "dual-head" state, maintaining both the new API layer and the legacy HTML-rendering views side-by-side. To achieve 100% compliance with the target architecture, these legacy artifacts and non-standard directories must be purged or fully migrated.

---

## 2. Structural Violations (Deviations from Target Architecture)

### 2.1. Root-Level [views.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/views.py) (Dual-Head Technical Debt)
- **Issue**: The target architecture mandates **Thin API views ONLY** inside the [api/views.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/api/views.py) folder. The presence of a 583-line [views.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/views.py) at the module root, which renders HTML templates (e.g., [render(request, 'filetracking/composefile.html')](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/placement_cell/views.py#5390-5410)), violates this strict decoupled API constraint.
- **Evidence**: [filetracking/views.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/views.py) contains endpoints like [filetracking()](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/views.py#26-90), [outbox_view()](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/views.py#129-183), and [drafts_view()](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/views.py#101-127) that wrap [services.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/services.py) logic but return HTML templates instead of JSON responses.
- **Impact**: Bloats the module, duplicates routing logic, and tightly couples the backend to Django templates.

### 2.2. Root-Level [urls.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/urls.py)
- **Issue**: The target architecture routes strictly through [api/urls.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/api/urls.py). The root [urls.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/urls.py) contains 24+ non-API path definitions (e.g., `path('draftdesign/', ...)`).
- **Evidence**: [filetracking/urls.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/urls.py) mixes legacy routes with `path('api/', include(api_urls))`.
- **Impact**: Fragmentation of URL structures and exposure of deprecated monolithic web paths.

### 2.3. Non-Standard [sdk/](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/services.py#315-319) Directory
- **Issue**: The module contains an [sdk/methods.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/sdk/methods.py) directory/file that is not part of the standard architecture.
- **Evidence**: [filetracking/sdk/methods.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/sdk/methods.py) exists as a duplicate abstraction layer. Many SDK methods have already been functionally duplicated or migrated into [services.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/services.py) (e.g., [create_draft_via_sdk](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/services.py#193-214)).
- **Impact**: Confusion over whether external modules should import from [sdk/](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/services.py#315-319) or [services.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/services.py).

### 2.4. Non-Standard [decorators.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/decorators.py) and [utils.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/utils.py)
- **Issue**: The target architecture does not include root-level [decorators.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/decorators.py) (48 lines) or [utils.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/utils.py) (13 lines).
- **Evidence**: 
  - [decorators.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/decorators.py) contains [user_is_student](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/decorators.py#27-34) which mixes logic with HTML rendering ([render(request, 'filetracking/fileTrackingNotAllowed.html')](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/placement_cell/views.py#5390-5410)).
  - [utils.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/utils.py) contains a single function ([get_designation](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/utils.py#11-14)) that merely acts as a redundant wrapper around `selectors.get_user_designations`.
- **Impact**: Logic fragmentation and violation of strict folder structure.

### 2.5. Constants in [models.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/models.py)
- **Issue**: [models.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/models.py) contains hardcoded constants (`MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024`) instead of confining constraints to serializers or Django settings, violating the strict [models.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/models.py) definition of "Models + TextChoices".

---

## 3. Code Redundancies

1. **[utils.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/utils.py) Wrapper**: `utils.get_designation(userid)` simply returns `selectors.get_user_designations(userid)`. Total redundancy.
2. **Double Validation**: The file size validation is handled both by `services.validate_file_size()` and an explicit check inside [api/views.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/api/views.py) `ForwardFileView.post()`.
3. **Session-based Routing**: HTML view redirects tightly couple logic to `request.session` (e.g., [get_designation_redirect_url_from_session](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/services.py#601-606) inside [services.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/services.py)), which is useless for a stateless REST API.

---

## 4. API Quality and Standards Validation

The current [api/](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/complaint_system/services.py#428-451) directory is **highly compliant**:
- **[api/serializers.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/api/serializers.py)**: Properly uses Input serializers ([FileCreateInputSerializer](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/api/serializers.py#42-49), [InboxQuerySerializer](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/api/serializers.py#66-71)) and separates Output serializers ([FileSerializer](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/api/serializers.py#9-18), [TrackingSerializer](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/api/serializers.py#20-29)). Fields are explicitly declared.
- **[api/views.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/api/views.py)**: Implements thin DRF [APIView](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/complaint_system/api/views.py#550-573) classes. Standardized token authentication and status codes (`HTTP_201_CREATED`, `HTTP_204_NO_CONTENT`). 
- **[api/urls.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/api/urls.py)**: Clean, RESTful routing mappings.

---

## 5. Refactoring Plan (Path to Strict Compliance)

To align completely with the target state without touching existing business logic in [services.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/services.py) or queries in [selectors.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/selectors.py), the following structural tear-down must occur:

### Phase 1: Purging the Legacy HTML Head
- **DELETE** [filetracking/views.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/views.py).
- **DELETE** [filetracking/urls.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/urls.py) (recreate it purely to standardly include [api/urls.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/api/urls.py), or move all routes into [api/urls.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/api/urls.py) directly).
- **DELETE** [filetracking/decorators.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/decorators.py). (The permissions logic should be handled by DRF `permission_classes` in [api/views.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/api/views.py)).

### Phase 2: Consolidating Non-Standard Files
- **DELETE** [filetracking/sdk/methods.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/sdk/methods.py) and the [sdk/](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/services.py#315-319) folder. Ensure any unique methods inside are mapped strictly within [services.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/services.py).
- **DELETE** [filetracking/utils.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/utils.py). Redirect any external imports pointing to `utils.get_designation` directly to `selectors.get_user_designations`.

### Phase 3: Cleanup of Services Layer
- **MODIFY** [services.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/services.py): Strip out session-dependency functions (e.g., [get_designation_redirect_url_from_session](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/services.py#601-606)) which were solely supporting the legacy [views.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/views.py) HTML workflow.

### Phase 4: Models & Serializers Optimization
- Move `MAX_FILE_SIZE_BYTES` into the serializer boundary ([api/serializers.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/api/serializers.py)) or Django settings to keep [models.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/models.py) purely focused on schema mapping.

### Validation
- Run the existing comprehensive [tests/test_module.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/tests/test_module.py) to ensure the API layer and [services.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/services.py) remain fully functional after pruning the legacy HTML views.
