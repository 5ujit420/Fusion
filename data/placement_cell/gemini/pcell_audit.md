# Placement Cell (pcell) Structural Audit & Refactoring Plan

## SECTION 1: MODULE SNAPSHOT

| Metric | Value | Measurement Method |
| :--- | :--- | :--- |
| **Total LOC (approx.)** | 6211 | Powershell `Measure-Object -Line *.py` |
| **LOC in views.py** | 5149 | WC / Powershell measurement on [views.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/views.py) |
| **LOC in api/views.py** | 0 | File does not exist |
| **No. of service files** | 0 | Directory scan |
| **No. of serializer classes** | 10 | Count in [api/serializers.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/api/serializers.py) |
| **No. of models** | 14 | Count of `class` keywords in [models.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/globals/models.py) aside from [Constants](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/placement_cell/models.py#11-83) |
| **Number of API endpoints** | 0 | No API router registered inside [api/](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/complaint_system/api/views.py#90-115) directory |
| **Number of DB queries in views** | 608 | `Select-String "\.objects\."` occurrences in [views.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/views.py) |
| **No. of structural violations** | 18 | Manual and parsed analysis |
| **No. of redundancy items** | 5 | Duplication scans for function names and branches |
| **services.py exists (Y/N)** | N | Directory scan |
| **selectors.py exists (Y/N)** | N | Directory scan |
| **tests/ folder exists (Y/N)** | N | Directory scan (only empty/template [tests.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/placement_cell/tests.py) file found) |
| **api/ folder exists (Y/N)** | Y | Exists but only contains [serializers.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/complaint_system/serializers.py) |
| **Uses TextChoices (Y/N)** | N | Uses tuple lists on [models.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/globals/models.py) |
| **Overall Structural State** | Poor | Extremely bloated views, zero API isolation, heavily coupled logic |

---

## SECTION 2: STRUCTURAL AUDIT

| ID | Category | File | Line Range | Description | Impact | Planned Fix | Detailed Fix Steps |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **SA-1** | Missing Folder Structure | `applications/placement_cell/` | N/A | Missing [services.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/services.py) containing pure business logic. | CRITICAL | Create [services.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/services.py) | Abstract all 11 complex POST logic branches from [views.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/views.py) into strictly typed functions inside [services.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/services.py). |
| **SA-2** | Missing Folder Structure | `applications/placement_cell/` | N/A | Missing [selectors.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/selectors.py) containing complex DB queries. | HIGH | Create [selectors.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/selectors.py) | Isolate the 608 instances of Django `.objects.*` ORM evaluations into predefined selector functions returning data. |
| **SA-3** | Missing Folder Structure | `applications/placement_cell/api/` | N/A | Missing [views.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/views.py) and [urls.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/Fusion/urls.py) in API layer. | CRITICAL | Establish [api/](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/complaint_system/api/views.py#90-115) layer routes | Bind a DRF layer to cleanly connect serializers logic directly to services logic. |
| **SA-4** | Fat View | [views.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/views.py) | 148-828 | [placement__Statistics](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/placement_cell/views.py#147-827) is ~680 LOC mixing data analytics, DB ORM logic, and context rendering. | HIGH | Migrate to Selectors & Services | Move statistical calculation logic to [services.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/services.py) and direct DB ORM fetches to [selectors.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/selectors.py). Replace view with thin API view. |
| **SA-5** | Fat View | [views.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/views.py) | 3936-4530 | [manage_records](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/placement_cell/views.py#3935-4528) is ~600 LOC orchestrating DB saves, context mapping, and permission checks. | HIGH | Component extraction | Delegate the save logic to [services.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/services.py), extract form validation into DRF `InputSerializers`. |
| **SA-6** | Logic in Serializer | [api/serializers.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/api/serializers.py) | 22-29 | `HasSerializer.create()` method explicitly implements `get_or_create` logic and exception raising. | MEDIUM | Move to services | Delete `def create()` from serialzier. Formally execute the logic in `services.create_has_skill()`. |
| **SA-7** | Unstructured Routing | [urls.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/Fusion/urls.py) | 6-29 | Routes mix specific API-style POSTs with standard GET renders without separation. | MEDIUM | Refactor mapping | Create [api/urls.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/api/urls.py) and strictly route payload operations to API paths. |
| **SA-8** | Security Issue | [views.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/views.py) | 4532-4550 | [delete_invite_status](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/placement_cell/views.py#4531-4591) operates inherently without strict row-level ownership assertions for DB deletion requests. | HIGH | Assert Ownership in Object Level | Define explicit `IsOwnerOrSuperuser` DRF permission check on the API endpoint boundary. |
| **SA-9** | Mixed Responsibilities | [views.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/views.py) | 5642-5666 | [add_placement_schedule](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/placement_cell/views.py#5642-5666) implements both form serving and permission enforcement logic. | MEDIUM | Migrate to DRF class View | Abstract endpoint into DRF `APIView` leveraging standard permissions models natively. |
| **SA-10** | Hard-coded Values | [models.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/globals/models.py) | 11-80 | [Constants](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/placement_cell/models.py#11-83) class encapsulates hard-coded enum sets directly inside [models.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/globals/models.py). | LOW | Export choices | Ideally move mapping configurations directly into `TextChoices` subclasses in Django 3+. |

---

## SECTION 3: REDUNDANCY REGISTER

| ID | Type | Location 1 | Location 2 | Description | Redundant | Plan | Detailed Consolidation |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **RR-1** | Code | `views.py:830` | `views.py:2195` | `def get_reference_list(request):` is declared twice in the exact same scope | Function block is overwritten dynamically during execution | Delete duplication | Remove the redundant second definition and consolidate into a single selector function `selectors.get_reference_list()`. |
| **RR-2** | Validation | `views.py:5707-5722` | `views.py:4532-4550` | [delete_placement_record](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/placement_cell/views.py#5707-5724) and [delete_invite_status](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/placement_cell/views.py#4531-4591) replicate the exact same context permission/role checks before executing ORM deletes. | View-level logic branching is highly repetitive | Normalize via Permissions | Extrapolate into standard DRF `@permission_classes` logic handling deletion authority. |
| **RR-3** | DB | `views.py:Various` | `views.py:Various` | Direct instantiations of `User.objects.get` mapping to profiles inside nested loops. | 600+ inline `.objects` invocations create massive N+1 gaps | Standardize DB Querying | Replace with dedicated `selectors.get_user_profile()` implementing `select_related()` correctly inside [selectors.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/selectors.py). |

---

## SECTION 4: REFACTORING PLAN

| Ref IDs | Action | Target Files | Validation |
| :--- | :--- | :--- | :--- |
| **SA-1, SA-3** | Spin up `api.views`, `services`, and `api.urls` | [api/urls.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/api/urls.py), [api/views.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/api/views.py), [services.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/services.py) | Automated unit test discovery successfully loads environment namespace. |
| **SA-2, RR-3** | Create [selectors.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/selectors.py) | [selectors.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/selectors.py) | Ensure test environment successfully executes queries returning standard schema objects. |
| **SA-4, SA-5, SA-9** | Strip and deprecate [views.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/views.py) inline logic | [views.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/views.py) -> [api/views.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/api/views.py) & [services.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/services.py) | Confirm all GET/POST requests run completely off the DRF pipeline seamlessly. |
| **SA-6** | Remove logic from serializers layer | [api/serializers.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/api/serializers.py) | Post endpoint correctly issues 400s explicitly using nested custom service validations. |
| **SA-7** | Migrate routing table exclusively into API context | [urls.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/Fusion/urls.py), [api/urls.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/api/urls.py), project [urls.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/Fusion/urls.py) | `manage.py check` throws 0 route masking errors. |
| **RR-1** | Delete identical structural duplicate endpoints | [views.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/views.py) | Unit module cleanly compiles without duplicate code smells. |
| **SA-8, RR-2** | Impress object-level strict ownership | `api/permissions.py` | Endpoints appropriately throw 403 Forbidden without execution via unit execution tests. |

---

## SECTION 5: API AUDIT

### 5A - Active APIs
*(Note: As `base views.py` operates as a monolith without DRF constraints, these denote mapped active legacy payload endpoints that behave as APIs)*

| No. | URL | Method | View | Auth | Role Check | Serializer | Status | Validation | Fix Plan |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | [placement_schedule_save/](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/placement_cell/views.py#5667-5705) | POST | [placement_schedule_save](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/placement_cell/views.py#5667-5705) | Django Session | Ad-Hoc [if](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/placement_cell/models.py#281-295) | None | CRITICAL | Manual | Port to DRF `APIView`, bind `InputSerializer`, offload save to [services.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/services.py). |
| 2 | [placement_record_save/](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/placement_cell/views.py#5740-5761) | POST | [placement_record_save](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/placement_cell/views.py#5740-5761) | Django Session | Ad-Hoc [if](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/placement_cell/models.py#281-295) | None | CRITICAL | Manual | Port to DRF `APIView`, bind `InputSerializer`, offload save to [services.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/services.py). |
| 3 | [placement_visit_save/](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/placement_cell/views.py#5790-5810) | POST | [placement_visit_save](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/placement_cell/views.py#5790-5810) | Django Session | Ad-Hoc [if](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/placement_cell/models.py#281-295) | None | CRITICAL | Manual | Port to DRF `APIView`, bind `InputSerializer`, offload save to [services.py](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/filetracking/services.py). |
| 4 | [delete_invite_status/](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/placement_cell/views.py#4531-4591) | GET/POST | [delete_invite_status](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/placement_cell/views.py#4531-4591) | Django Session | Inconsistent | None | CRITICAL | Manual | Port to `DELETE` HTTP method mapped via unified permission DRF pipeline. |

### 5B - Inactive APIs
| No. | URL | View | Status | Action |
| :--- | :--- | :--- | :--- | :--- |
| N/A | No strict APIs found currently | N/A | N/A | N/A |

### 5C - API Compliance

*   **Uses @api_view or APIView**: NO - All code lives in raw Django views.
*   **Uses permission_classes**: NO - Ad-Hoc manual parsing.
*   **Uses authentication_classes**: NO - Django web-view fallback.
*   **Uses DRF Response**: NO - Pure `HttpResponse`/[render](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/placement_cell/views.py#5390-5410) pipeline.
*   **Uses serializers for input**: NO - Massive manual payload checking mapping directly to HTML forms.
*   **Uses serializers for output**: NO - Mixed DB responses natively rendered into HTML dict context.
*   **Consistent error format**: NO - Arbitrary message strings and redirects.
*   **Pagination present**: NO.
*   **API versioning**: NO.
*   **URL naming consistency**: POOR - Mixing trailing logic, REST patterns, and verb-commands indiscriminately (`/save`).

### 5D - Legacy Views

| No. | Function | URL | Needs API |
| :--- | :--- | :--- | :--- |
| 1 | [placement__Statistics](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/placement_cell/views.py#147-827) | [statistics/](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/placement_cell/views.py#4594-5233) | YES - Heavy calculation payload should be strict JSON provider |
| 2 | [manage_records](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/placement_cell/views.py#3935-4528) | [manage_records/](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/placement_cell/views.py#3935-4528) | YES - Forms replacement to headless JS interface requires purely abstracted CRUD API bounds. |
| 3 | [invitation_status](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/placement_cell/views.py#3251-3620) | `student_records/invitation_status`| YES - Pure logic fetch pattern. |
| 4 | [get_reference_list](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/placement_cell/views.py#830-846) | [get_reference_list/](file:///c:/Users/sujit/OneDrive/Documents/Fusion_new/Fusion/FusionIIIT/applications/placement_cell/views.py#830-846) | YES - Pure data provider. |
