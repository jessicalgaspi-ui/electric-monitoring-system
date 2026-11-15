# Smart-Grid Intelligence Platform — Test Cases

Manual functional and edge-case test checklist for the Streamlit application.
Record the result of each test as **Pass**, **Fail**, or **Blocked**, and note
the test date, app version, database backend, and any failure details.

## Test setup

- Install dependencies and start the app as described in [README.md](README.md).
- Test locally with SQLite first. If PostgreSQL/Neon is configured, repeat
  the persistence and startup tests against a separate demo database.
- Use synthetic/demo records only. Never test with real household or payment
  data.
- Back up the local database before tests that add or delete records. Use a
  disposable test database for deletion, migration, and recovery tests.
- Administrator sign-in requires valid credentials in Streamlit secrets.
  Seeded resident accounts are sign-in ready only when a demo password has
  been provisioned; otherwise, use the resident account-creation flow.
- Payments are recorded by this app; they do not charge a real payment
  provider.

## Test cases

| ID | Area | Test and steps | Expected result |
|---|---|---|---|
| TC-001 | Startup | Start the app from the project directory using `python -m streamlit run app.py`. | App starts without an exception; database schema initializes and the Welcome page is displayed. |
| TC-002 | Startup / portability | Copy the project to a different writable folder and start it there. | App starts and its SQLite database and generated files use the copied project folder, not the original absolute path. |
| TC-003 | Startup / secrets | Start without `.streamlit/secrets.toml`. | Resident features remain available; administrator login is unavailable or reports that admin credentials are not configured, without crashing the app. |
| TC-004 | Startup / database | Start against an empty disposable SQLite database. | Schema and baseline synthetic data initialize once; a subsequent restart does not duplicate seed data. |
| TC-005 | Authentication | Submit resident sign-in with both fields empty. | A required-fields validation message appears; no sign-in occurs. |
| TC-006 | Authentication | Sign in with an unknown account number. | A clear account-not-found message appears; no protected resident pages are accessible. |
| TC-007 | Authentication | Sign in with an existing registered account and an incorrect password. | Sign-in is rejected with a clear error; account data is not exposed. |
| TC-008 | Authentication | Sign in with an existing account number in different letter casing and the correct password. | Account lookup is case-insensitive and sign-in succeeds. |
| TC-009 | Authentication | Attempt to sign in to a seeded, unclaimed account. | The app explains that the account is not registered and directs the resident to account creation. |
| TC-010 | Authentication | Sign in with configured administrator credentials. | Administrator navigation and pages are shown. |
| TC-011 | Authentication / authorization | Open an administrator-only page while signed out or signed in as a resident. | Admin-only data and actions are not accessible; the app returns to or displays the appropriate access/login state. |
| TC-012 | Authentication | Log out, then use browser back or reload. | Session is cleared; protected views are not usable without signing in again. |
| TC-013 | Account creation | Create a resident account with valid unique account number, required details, matching password of at least six characters, and valid coordinates. | Account is created, the resident is signed in, and the new account remains available after reload. |
| TC-014 | Account creation / validation | Submit account creation with one required field missing. | Submission is rejected with a validation message; no partial account is stored. |
| TC-015 | Account creation / validation | Try account numbers such as `8001`, `ACC-12`, or an account number containing spaces. | Invalid format is rejected; account numbers must use `ACC-` followed by at least four digits. |
| TC-016 | Account creation / duplicate | Register an existing account number, including a different-case version of it. | Duplicate account is rejected without creating a second account. |
| TC-017 | Account creation / password | Use a password shorter than six characters or enter non-matching confirmation. | Account creation is rejected with a relevant validation message. |
| TC-018 | Account creation / coordinates | Leave both coordinates empty, enter only one coordinate, or enter non-numeric text. | Registration without both valid coordinates is rejected and no account is created. |
| TC-019 | Account creation / coordinates | Enter latitude outside `-90..90` or longitude outside `-180..180`. | Out-of-range coordinates are rejected. |
| TC-020 | Household management | As admin, add a household with valid details and coordinates. | Household appears in the directory and is available for recording readings. |
| TC-021 | Household management / validation | Add a household with blank required fields, an invalid account number, unsupported type/status, or a duplicate account number. | Invalid data is rejected; existing household records remain unchanged. |
| TC-022 | Household management / search | Search by partial account number, partial homeowner name, mixed-case text, and a string containing regex characters (for example `[` or `.`). | Search is literal and case-insensitive; matching results are shown without a regex error. |
| TC-023 | Household management / filters | Filter household directory by Residential and Commercial, then clear the filter. | Each filter shows only the selected type; clearing returns all records. |
| TC-024 | Household coordinates | Save a complete valid coordinate pair for a household and reload the map. | Saved coordinates persist and the household pin uses the saved location. |
| TC-025 | Household coordinates / edge cases | Save only one coordinate, non-numeric values, or values outside valid geographic ranges. | Update is rejected with a validation message; previously saved coordinates are not partially overwritten. |
| TC-026 | Meter readings | As admin, record a first reading with valid period, date within that period, non-negative readings, and positive rate. | Reading is stored; usage equals current minus previous; estimated cost equals usage multiplied by rate. |
| TC-027 | Meter readings / continuity | Record a later-period reading whose previous value equals the household's last current reading. | Reading saves successfully and appears in the records and resident history. |
| TC-028 | Meter readings / validation | Try a current reading lower than the previous reading, a negative previous reading, or a zero/negative rate. | Invalid reading is rejected; no record is added. |
| TC-029 | Meter readings / period | Enter malformed period, such as `2026/01` or `2026-13`, or a reading date outside the selected billing month. | Reading is rejected with a clear date/period validation message. |
| TC-030 | Meter readings / duplicate | Record two readings for the same household and billing period. | The second reading is rejected; the first remains unchanged. |
| TC-031 | Meter readings / continuity edge | For a later billing period, use a previous reading different from the last recorded current reading. | Reading is rejected and the expected previous value is explained. |
| TC-032 | Meter readings / search | Search by partial account/name and filter by connection type and billing period. | Results and totals reflect all active filters; clearing filters restores the full list. |
| TC-033 | Resident dashboard | Sign in as a resident with readings and open the dashboard and reading history. | Only that household's readings and relevant usage summaries are shown. |
| TC-034 | Resident dashboard / empty state | Sign in as a newly registered account with no readings. | Empty state is displayed without a crash or another household's data. |
| TC-035 | Billing / payment | Pay an unpaid reading using its exact statement amount and a supported gateway. | Payment is recorded once, a reference is shown, and the statement is no longer presented as unpaid. |
| TC-036 | Billing / amount validation | Try zero, negative, non-numeric, or an amount that differs from the statement by more than one cent. | Payment is rejected; no payment record is created. |
| TC-037 | Billing / authorization | Attempt to pay another household's reading or a nonexistent reading. | Payment is rejected as not owned/not found; no payment record is created. |
| TC-038 | Billing / duplicate | Attempt to pay an already paid statement a second time. | Duplicate payment is rejected; only the original payment is retained. |
| TC-039 | Billing / gateway | Submit an unsupported gateway value through the payment flow. | Payment is rejected and the supported gateway choices are communicated. |
| TC-040 | Outage report | As resident, submit a report with issue type, severity, details, and date. | Report is saved, associated with the resident's barangay, and appears in the resident feed and admin incident registry. |
| TC-041 | Outage report / validation | Submit with empty details. | Report is not submitted; a prompt asks for a description. |
| TC-042 | Incident registry | As admin, log an incident with valid barangay, type, severity, and date; filter by severity and barangay. | Incident persists and appears in the expected filtered results. |
| TC-043 | Incident registry / validation | Submit blank barangay/type, invalid severity, or an invalid date string through the data layer. | Operation is rejected; no incident is stored. |
| TC-044 | GIS map | Open admin GIS and resident area maps with seeded records and incidents. | Map renders; pins correspond to saved or documented approximate locations, and resident map scope is limited to the resident's area. |
| TC-045 | GIS map / empty coordinates | Use a household with missing coordinates or an incident without exact coordinates. | Map handles the missing exact location using its documented approximation behavior or omits the pin gracefully; no crash occurs. |
| TC-046 | Analytics | Open Analytics with populated readings and inspect monthly trend, connection-type comparison, gallery charts, and PNG export options. | Charts render from current database data, labels and totals are plausible, and each available PNG export downloads as an image. |
| TC-047 | Analytics / sparse data | Open Analytics with no readings, then with only one or two data points in a disposable database. | Empty states or charts handle sparse inputs without an unhandled exception. |
| TC-048 | Analytics / chart set | Verify outlier, clustering, forecast, tariff-tier, and disaster correlation charts when their input data is available. | Each chart is readable, uses the app's navy/teal/sky/amber palette, and accurately reflects its input data. |
| TC-049 | Exports | Download household and reading CSVs, a PDF report, and the executive Markdown report. | Files download/open successfully, contain expected columns/content, and do not include passwords or password hashes. |
| TC-050 | Audit trail | Add a household, record a reading, record an incident, and complete a payment; inspect the audit page. | Corresponding actions are logged with useful targets/details and appear in newest-first order. |
| TC-051 | Persistence | Create a test account/reading/incident/payment, restart the app, and read the records again. | Records remain in the configured database. SQLite and PostgreSQL test results are evaluated separately. |
| TC-052 | Database migration | Start the app more than once against an existing populated database. | Schema/data migrations are repeatable and do not replace user records or duplicate synthetic households/payments. |
| TC-053 | PostgreSQL | With an SSL-enabled PostgreSQL URL configured in Streamlit secrets, start against an empty disposable Neon database and exercise account, reading, and payment flows. | PostgreSQL schema initializes; supported operations work and data persists after app restart. |
| TC-054 | PostgreSQL / configuration | Start with a malformed/unreachable database URL in a test deployment. | Startup/configuration failure is visible and actionable; the app must not silently report successful PostgreSQL persistence while using a different database. |
| TC-055 | Deployment / secrets | Deploy with Streamlit secrets configured; inspect repository/source and logs. | No database URL, password, or other secret is exposed in source, UI output, or normal logs. |
| TC-056 | Deployment / network | Open the deployed app from a separate browser/device and perform a safe demo sign-in. | Hosted app renders and its behavior matches the configured hosted database; no local database records are assumed to be uploaded. |

## Edge-case checklist

- [ ] Database contains no households, readings, payments, or incidents.
- [ ] Database contains households but no readings; analytics and reading pages
  display safe empty states.
- [ ] Account numbers differ only by letter case.
- [ ] Text inputs contain leading/trailing whitespace, Unicode names, apostrophes,
  punctuation, and very long text.
- [ ] Numeric values are zero, negative, fractional, extremely large, or
  non-numeric where applicable.
- [ ] Coordinates lie exactly on valid boundaries (`-90`, `90`, `-180`, `180`)
  and just outside those boundaries.
- [ ] A billing period is duplicated or not later than the previous recorded
  period; continuity rules are respected.
- [ ] A reading has zero usage (current equals previous); cost remains zero and
  is handled consistently with payment rules.
- [ ] A statement is paid twice, with a different gateway, or for the wrong
  household.
- [ ] A household has no saved map coordinates, or a disaster has only
  barangay-level location information.
- [ ] There are too few observations for quartiles, clustering, regression, or
  anomaly calculations.
- [ ] Search has no matches or includes literal regex punctuation.
- [ ] A CSV/PDF/chart is requested with no source data.
- [ ] App restarts while the database is empty, populated, or temporarily
  unreachable.
- [ ] Streamlit secrets are missing, malformed, or contain incomplete
  administrator/database sections.
- [ ] Local SQLite and hosted PostgreSQL each receive distinct test records;
  verify there is no implicit transfer between them.
- [ ] A user reloads, logs out, uses browser back, or opens a protected URL
  without the required role.
- [ ] A generated chart is checked for readable text, correct chart values,
  app-matching colors, valid PNG format, and successful opening in an image
  viewer.

## Test run record

| Date | App version/commit | Environment | Database | Passed | Failed | Blocked | Notes |
|---|---|---|---|---:|---:|---:|---|
| YYYY-MM-DD |  | Local / hosted | SQLite / PostgreSQL |  |  |  |  |

