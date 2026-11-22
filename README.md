# Smart-Grid Intelligence Platform

**Household Accounts, Meter Readings, Billing, Analytics, Incident Reporting & GIS Dashboard**  
DSA 214 – Data Science and Analytics Project

Smart-Grid Intelligence Platform is a Python Streamlit application for managing residential and commercial electricity accounts, recording meter readings, handling billing and payment histories, reporting grid incidents, analyzing consumption trends, and viewing GIS map layers.

> **Current release:** This repository contains the Streamlit dashboard version of the Smart-Grid Intelligence Platform. The application uses a local SQLite database stored at `data/electricity_monitor.db` and does not require a separate hosted database server.

---

## Table of Contents

- [Features](#features)
- [Technology Stack](#technology-stack)
- [Requirements](#requirements)
- [Getting Started](#getting-started)
- [Configuration](#configuration)
- [Running Smart-Grid Intelligence Platform](#running-smart-grid-intelligence-platform)
- [Using the Application](#using-the-application)
- [Demo Data and GIS Mapping](#demo-data-and-gis-mapping)
- [Project Structure](#project-structure)
- [Troubleshooting](#troubleshooting)
- [Security Notes](#security-notes)
- [Project Team](#project-team)

---

## Features

### Household and Account Management
- Manage residential (person-named) and commercial (business-named) electricity accounts with varied account statuses.
- Enforce case-insensitive account-number uniqueness on new resident registrations and administrator-added households.
- Prevent claiming existing accounts through resident sign-up; new registrations must use an unused account number.
- Validate latitude and longitude coordinate ranges when creating or updating household records.

### Meter Readings and Billing
- Record and track meter readings and electricity consumption per household account.
- Maintain billing and payment histories, keeping unpaid readings visible as outstanding statements.
- Tag generated demo transactions with the `SYN-` payment reference prefix.

### Analytics and Executive Reporting
- Explore consumption, billing, and payment patterns across the dashboard.
- Regenerate the Markdown executive summary report on demand via `executive_report.py`.

### Incident Reporting and GIS Views
- Log and view emergency and incident reports associated with barangays.
- Visualize household locations and incident pins on interactive GIS map views.
- Estimate missing household coordinates from mapped households in the same barangay when available, or update pins directly from the **Households** page.

**Important:** Seeded demo coordinates, synthetic households, and generated `SYN-` transactions are for demonstration and testing purposes. They should not be treated as verified home addresses or live utility billing records.

---

## Technology Stack

- **Python** – application runtime and executive report generation
- **Streamlit** – interactive web dashboard interface
- **SQLite** – local relational database (`data/electricity_monitor.db`)
- **OpenStreetMap** – community and public-place reference coordinates used for seeded demo pins

---

## Requirements

Before installing and running the application, make sure you have:

1. Python 3.10 or later installed.
2. Git installed (if cloning the repository).
3. Administrator credentials configured in `.streamlit\secrets.toml`.
4. Access to the temporary demo password (if seeding or using demo resident accounts outside source control).

You do **not** need to install an external database server or manually create `data\electricity_monitor.db` beforehand. The SQLite database is initialized automatically when the application starts.

Check that Python and pip are available:

```powershell
python --version
python -m pip --version
```

On some systems, use `py` instead of `python`.

---

## Getting Started

### 1. Download or clone the repository

Using Git:

```powershell
git clone https://github.com/jessicalgaspi-ui/electric-monitoring-system.git
cd electric-monitoring-system
```

Alternatively, download the repository as a ZIP file from GitHub, extract it, and open PowerShell in the extracted project folder.

### 2. Create a virtual environment (recommended)

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, you can use Command Prompt:

```bat
.venv\Scripts\activate.bat
```

A virtual environment keeps this project's Python packages separate from other Python projects.

### 3. Install dependencies

From the project root, run:

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

The `requirements.txt` file includes the Streamlit, database, data-handling, and mapping dependencies used by the application.

---

## Configuration

Smart-Grid Intelligence Platform reads administrator credentials from a secrets file named `.streamlit\secrets.toml`, located inside the `.streamlit` directory.

### 1. Create your `secrets.toml` file

Copy `.streamlit\secrets.toml.example` and name the copy `.streamlit\secrets.toml`.

Windows PowerShell:

```powershell
Copy-Item .streamlit\secrets.toml.example .streamlit\secrets.toml
```

If you are using Command Prompt:

```bat
copy .streamlit\secrets.toml.example .streamlit\secrets.toml
```

### 2. Set administrator credentials

Open `.streamlit\secrets.toml` in a text editor and replace both placeholder values with your own administrator credentials.

Do not:
- Commit `.streamlit\secrets.toml` to Git.
- Upload `.streamlit\secrets.toml` to GitHub.
- Store the temporary demo password in source control.
- Share credentials, passwords, or secrets in screenshots, chat messages, or public issue reports.

The `.streamlit\secrets.toml` file should remain ignored by Git so local credentials are not exposed in the repository.

---

## Running Smart-Grid Intelligence Platform

Make sure your virtual environment is active and your `.streamlit\secrets.toml` file is configured.

Start the application from the project root:

```powershell
python -m streamlit run app.py
```

On startup, the application initializes `data\electricity_monitor.db` automatically if it does not already exist.

The application does **not** erase or reseed existing records during normal startup. Do **not** run `python database.py --reset` unless you intend to erase and reseed that data.

### Regenerating the Executive Summary

To regenerate the Markdown executive summary report, run:

```powershell
python executive_report.py
```

---

## Using the Application

Navigate across the dashboard views to manage accounts, meter readings, billing, incidents, analytics, and maps:

- **Households** – browse accounts, register or add households with valid latitude and longitude coordinates, and update map pins with verified GPS or map-pin coordinates.
- **Meter Readings & Billing** – record and inspect meter usage, view payment histories (including `SYN-` demo transactions), and track unpaid readings as outstanding statements.
- **Incident Reporting** – log and review emergency and incident reports associated with barangays.
- **Analytics & GIS Views** – review consumption and billing analytics and inspect household and barangay incident pins on the map.

Follow the prompts shown in the dashboard. Provide both latitude and longitude when registering new resident accounts or adding households, and use an unused account number for new resident sign-ups.

---

## Demo Data and GIS Mapping

The local SQLite database supports seeded and synthetic demonstration records alongside live entries.

During initialization, seeded accounts (`ACC-8001` through `ACC-8010`) use the shared temporary password provided to the operator (not stored in source control). When a seeded demo password is available, initialization also adds 19 synthetic demo households—bringing the current provisioned database total to 30 households—reusing the configured demo-account password hash without storing the plaintext password in source control.

For demo and mapping behavior:

1. New resident registrations must use an unused account number; existing accounts cannot be claimed through sign-up.
2. Account-number uniqueness is enforced without regard to letter case, and coordinate ranges are validated on new and updated households.
3. Seeded demo coordinates are approximate barangay or locality positions (with Echague demo pins using mapped locations in Echague rather than old points north of its town area), not exact household locations.
4. Synthetic demo accounts use OpenStreetMap community or public-place coordinates as locality approximations—not exact home addresses—with person names for residential accounts and business names for commercial accounts.
5. Households without saved coordinates are estimated from mapped households in the same barangay when possible, and administrators can replace any approximate pin with verified GPS or map-pin coordinates from the **Households** page.
6. Emergency reports contain a barangay rather than an exact location, so their map pins are approximate barangay locations.
7. Synthetic households have varied account statuses, meter usage, and payment histories; payment references prefixed with `SYN-` identify generated demo transactions, while unpaid readings remain visible as outstanding statements.

This migration is additive and does not replace existing households or payments.

---

## Project Structure

Important files and directories in the repository:

| File / Path | Purpose |
|---|---|
| `app.py` | Main Streamlit dashboard application and page views |
| `database.py` | SQLite initialization, schema migrations, queries, and `--reset` seeding support |
| `executive_report.py` | Generates and regenerates the Markdown executive summary report |
| `data/electricity_monitor.db` | Local SQLite database file |
| `.streamlit/secrets.toml.example` | Example Streamlit secrets file containing credential placeholders |
| `.streamlit/secrets.toml` | Local administrator credentials file |
| `requirements.txt` | Python package dependencies |

Other helper or report files may be present in the repository depending on your working tree.

---

## Troubleshooting

### Missing or invalid `.streamlit\secrets.toml`

- Confirm that the file is named `.streamlit\secrets.toml` inside the `.streamlit` folder.
- Confirm that both placeholder values from `.streamlit\secrets.toml.example` were replaced with valid administrator credentials.
- Make sure you did not save the file with an extra extension such as `.toml.txt`.

### Database connection, lock, or reset issues

- Confirm that `data\electricity_monitor.db` is accessible and not locked by another running process.
- Avoid running `python database.py --reset` unless you intentionally want to erase and reseed the SQLite database.

### `ModuleNotFoundError`

Activate the project's virtual environment and run:

```powershell
python -m pip install -r requirements.txt
```

If the error continues, confirm that the same Python interpreter is being used to install packages and run `python -m streamlit run app.py`.

### Resident sign-up is rejected

- Check that the account number is not already in use (account-number uniqueness is case-insensitive).
- Confirm that you are not attempting to claim an existing or seeded account through sign-up.
- Confirm that both latitude and longitude are entered and within valid coordinate ranges.

### Map pins look approximate or are missing

- Remember that seeded and synthetic pins use approximate barangay, community, or OpenStreetMap locality coordinates rather than exact street addresses, and emergency reports plot at approximate barangay locations.
- For households without saved coordinates, check whether other mapped households exist in the same barangay for estimation, or update the pin directly from the **Households** page with verified GPS or map-pin coordinates.

---

## Security Notes

- Never commit `.streamlit\secrets.toml` or expose credentials in repositories or screenshots.
- Do not store temporary demo passwords or password hashes' plaintext passwords in source control.
- Do not run `python database.py --reset` against data you want to preserve.
- Treat household account records, meter readings, billing histories, and incident reports as private project data.

---

## Project Team

- Kristine De Vera
- Aldwyn Delmendo
- Abegail Domingo
- Jessica Lagmay

---

**Smart-Grid Intelligence Platform – Household Accounts, Meter Readings, Billing, Analytics, Incident Reporting & GIS Dashboard**
