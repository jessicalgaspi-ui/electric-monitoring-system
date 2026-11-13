# Smart-Grid Intelligence Platform

Streamlit dashboard for household accounts, meter readings, billing,
analytics, incident reporting, and GIS views.

## Run on Windows

From PowerShell, open the project folder and install its dependencies:

```powershell
cd "C:\path\to\smart-grid-monitor"
python -m pip install -r requirements.txt
```

Create `.streamlit\secrets.toml` from
[`.streamlit\secrets.toml.example`](.streamlit/secrets.toml.example), then
replace both placeholder values with your own administrator credentials.
Do not commit `secrets.toml`.

Start the app:

```powershell
python -m streamlit run app.py
```

## Demo resident accounts

In the currently provisioned local database, seeded accounts `ACC-8001`
through `ACC-8010` use the shared temporary password provided to the operator.
New resident registrations must use an unused account number; existing
accounts cannot be claimed through sign-up. The temporary password is not
stored in source control.

The SQLite database is stored at `data\electricity_monitor.db` and is
initialized automatically when the app starts. Do not run
`python database.py --reset` unless you intend to erase and reseed that data.

Household map pins use the latitude and longitude stored on each household.
Seeded demo coordinates are approximate barangay or locality positions, not
exact household locations. Echague demo pins now use mapped locations in
Echague rather than the old points north of its town area. An administrator
can replace any approximate pin with verified GPS or map-pin coordinates from
the Households page. Households without saved coordinates are estimated from
mapped households in the same barangay when possible. Emergency reports
contain a barangay rather than an exact location, so their map pins are
approximate barangay locations.

New resident registrations and administrator-added households must provide
both latitude and longitude. The database validates coordinate ranges and
enforces account-number uniqueness without regard to letter case. During
initialization, the database adds 19 synthetic demo households when a seeded
demo password is available. In the current provisioned database, this brings
the household total to 30. These accounts reuse the configured demo-account
password hash; the password itself
is not stored in source control. Their location pins use mapped community or
public-place coordinates from OpenStreetMap and are locality approximations,
not exact home addresses. Synthetic residential accounts use person names and
commercial accounts use business names; all remain synthetic demo records.

Synthetic households have varied account statuses, meter usage, and payment
histories. Payment references prefixed with `SYN-` identify generated demo
transactions; unpaid readings remain visible as outstanding statements. This
additive migration does not replace existing households or payments.

Regenerate the Markdown executive summary with:

```powershell
python executive_report.py
```