"""Data-access and validation layer.

Merged from:
  - the Streamlit rewrite's CHECK-constrained validation, continuity checks,
    and (success, message) tuple returns, with
  - the teammate's audit logging, disaster incident CRUD, and cascade-delete
    helpers, adapted to the new schema,
  - password-based registration and login for residents (salted PBKDF2),
  - a payments sub-system (record, query, dedupe by reading).
"""
import re
import secrets
import sqlite3
from contextlib import closing
from datetime import datetime

from database import get_connection, hash_password, verify_password

VALID_TYPES = ("Residential", "Commercial")
VALID_STATUSES = ("Active", "Inactive", "Overdue", "Suspended", "Disconnected")
VALID_GATEWAYS = ("GCash", "Maya", "Bank Transfer", "Cash", "Manual")
ACCOUNT_PATTERN = re.compile(r"ACC-\d{4,}")


# ---------------------------------------------------------------------------
# Reads — households
# ---------------------------------------------------------------------------
def fetch_all_households():
    with closing(get_connection()) as conn:
        return conn.execute("""
            SELECT household_id, account_number, homeowner_name, address,
                   connection_type, status
            FROM households ORDER BY household_id
        """).fetchall()


def fetch_all_households_geo():
    with closing(get_connection()) as conn:
        return conn.execute("""
            SELECT household_id, account_number, homeowner_name, address,
                   connection_type, status, latitude, longitude
            FROM households ORDER BY household_id
        """).fetchall()


def fetch_demo_accounts():
    """Return login-ready seeded and synthetic demo accounts for the landing page."""
    with closing(get_connection()) as conn:
        return conn.execute("""
            SELECT account_number, homeowner_name, address
            FROM households
            WHERE password_hash IS NOT NULL
              AND (
                  CAST(SUBSTR(account_number, 5) AS INTEGER) BETWEEN 8001 AND 8010
                  OR CAST(SUBSTR(account_number, 5) AS INTEGER) BETWEEN 8012 AND 8030
              )
            ORDER BY account_number
        """).fetchall()


def get_household_by_id(household_id):
    with closing(get_connection()) as conn:
        return conn.execute("""
            SELECT household_id, account_number, homeowner_name, address,
                   connection_type, status, online_billing, latitude, longitude
            FROM households WHERE household_id = ?
        """, (household_id,)).fetchone()


def update_household_coordinates(household_id, latitude, longitude):
    """Save a verified coordinate pair, or clear both coordinates."""
    latitude, longitude, coordinate_error = parse_coordinate_pair(
        latitude, longitude, allow_empty=True
    )
    if coordinate_error:
        return False, coordinate_error

    try:
        with closing(get_connection()) as conn, conn:
            result = conn.execute("""
                UPDATE households
                SET latitude = ?, longitude = ?, updated_at = CURRENT_TIMESTAMP
                WHERE household_id = ?
            """, (latitude, longitude, household_id))
            if result.rowcount != 1:
                return False, "Household not found."
    except sqlite3.Error as e:
        return False, f"Database error: {e}"

    coordinates = "cleared" if latitude is None else f"{latitude:.6f}, {longitude:.6f}"
    log_audit_event("UPDATE_HOUSEHOLD_COORDINATES", household_id, coordinates)
    return True, "Household coordinates updated."


# ---------------------------------------------------------------------------
# Reads — readings
# ---------------------------------------------------------------------------
def fetch_all_readings():
    with closing(get_connection()) as conn:
        return conn.execute("""
            SELECT r.reading_id, h.account_number, h.homeowner_name,
                   r.billing_period, r.previous_reading, r.current_reading,
                   r.consumption_kwh, r.rate_per_kwh, r.estimated_cost,
                   r.reading_date, h.connection_type
            FROM meter_readings r
            JOIN households h ON r.household_id = h.household_id
            ORDER BY r.reading_date DESC, r.reading_id DESC
        """).fetchall()


def get_last_reading(household_id):
    with closing(get_connection()) as conn:
        return conn.execute("""
            SELECT billing_period, current_reading, rate_per_kwh
            FROM meter_readings WHERE household_id = ?
            ORDER BY billing_period DESC LIMIT 1
        """, (household_id,)).fetchone()


# ---------------------------------------------------------------------------
# Reads — search / filter
# ---------------------------------------------------------------------------
def search_account_records(acc_query):
    with closing(get_connection()) as conn:
        return conn.execute("""
            SELECT h.account_number, h.homeowner_name, h.address,
                   h.connection_type, r.billing_period,
                   r.previous_reading, r.current_reading,
                   r.consumption_kwh, r.rate_per_kwh, r.estimated_cost,
                   r.reading_date
            FROM households h
            LEFT JOIN meter_readings r ON h.household_id = r.household_id
            WHERE h.account_number LIKE ? OR h.homeowner_name LIKE ?
            ORDER BY h.account_number, r.billing_period
        """, (f"%{acc_query}%", f"%{acc_query}%")).fetchall()


def filter_readings_by_type(connection_type):
    with closing(get_connection()) as conn:
        return conn.execute("""
            SELECT h.account_number, h.homeowner_name, h.connection_type,
                   r.billing_period, r.consumption_kwh, r.estimated_cost
            FROM meter_readings r
            JOIN households h ON r.household_id = h.household_id
            WHERE h.connection_type = ?
            ORDER BY r.consumption_kwh DESC
        """, (connection_type,)).fetchall()


def get_highest_consumer():
    with closing(get_connection()) as conn:
        return conn.execute("""
            SELECT h.account_number, h.homeowner_name, h.address,
                   h.connection_type,
                   SUM(r.consumption_kwh) AS total_usage,
                   SUM(r.estimated_cost)  AS total_cost
            FROM meter_readings r
            JOIN households h ON r.household_id = h.household_id
            GROUP BY h.household_id
            ORDER BY total_usage DESC LIMIT 1
        """).fetchone()


# ---------------------------------------------------------------------------
# Reads — audit & disasters
# ---------------------------------------------------------------------------
def fetch_audit_logs(limit=200):
    with closing(get_connection()) as conn:
        return conn.execute("""
            SELECT log_id, timestamp, action, target, details
            FROM audit_logs ORDER BY log_id DESC LIMIT ?
        """, (limit,)).fetchall()


def fetch_disaster_incidents(limit=200):
    with closing(get_connection()) as conn:
        return conn.execute("""
            SELECT incident_id, date_reported, barangay, incident_type,
                   severity_level
            FROM disaster_incidents
            ORDER BY date_reported DESC, incident_id DESC LIMIT ?
        """, (limit,)).fetchall()


# ---------------------------------------------------------------------------
# Reads — payments
# ---------------------------------------------------------------------------
def get_unpaid_bills(household_id):
    with closing(get_connection()) as conn:
        return conn.execute("""
            SELECT r.reading_id, r.billing_period, r.consumption_kwh,
                   r.estimated_cost, r.reading_date
            FROM meter_readings r
            WHERE r.household_id = ?
              AND NOT EXISTS (
                  SELECT 1 FROM payments p WHERE p.reading_id = r.reading_id
              )
            ORDER BY r.billing_period DESC
        """, (household_id,)).fetchall()


def fetch_payments_for_household(household_id):
    with closing(get_connection()) as conn:
        return conn.execute("""
            SELECT p.payment_id, p.paid_at, p.amount_paid, p.gateway,
                   p.reference_no, r.billing_period
            FROM payments p
            JOIN meter_readings r ON r.reading_id = p.reading_id
            WHERE p.household_id = ?
            ORDER BY p.paid_at DESC
        """, (household_id,)).fetchall()


def fetch_all_payments(limit=200):
    with closing(get_connection()) as conn:
        return conn.execute("""
            SELECT p.payment_id, p.paid_at, h.account_number, h.homeowner_name,
                   r.billing_period, p.amount_paid, p.gateway, p.reference_no
            FROM payments p
            JOIN households h     ON h.household_id = p.household_id
            JOIN meter_readings r ON r.reading_id    = p.reading_id
            ORDER BY p.paid_at DESC
            LIMIT ?
        """, (limit,)).fetchall()


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------
def authenticate_resident(account_number, password):
    """Returns (success: bool, household_dict | error_message)."""
    account_number = (account_number or "").strip()
    password = (password or "").strip()

    if not account_number or not password:
        return False, "Account number and password are required."

    try:
        with closing(get_connection()) as conn:
            row = conn.execute("""
                SELECT household_id, account_number, homeowner_name, address,
                       connection_type, status, password_hash
                FROM households
                WHERE UPPER(account_number) = UPPER(?)
            """, (account_number,)).fetchone()
    except sqlite3.Error as e:
        return False, f"Database error: {e}"

    if not row:
        return False, "No account found with that number."
    if row["password_hash"] is None:
        return False, ("This account hasn't been registered yet. "
                       "Switch to 'Create Account' to activate it.")
    if not verify_password(password, row["password_hash"]):
        return False, "Incorrect password."

    household = {k: row[k] for k in row.keys() if k != "password_hash"}
    return True, household


def parse_coordinate_pair(latitude, longitude, allow_empty=False):
    """Parse and validate a latitude/longitude pair."""
    latitude = ("" if latitude is None else str(latitude)).strip()
    longitude = ("" if longitude is None else str(longitude)).strip()
    if not latitude and not longitude and allow_empty:
        return None, None, None
    if not latitude or not longitude:
        return None, None, "Enter both latitude and longitude."
    try:
        latitude, longitude = float(latitude), float(longitude)
    except ValueError:
        return None, None, "Latitude and longitude must be valid numbers."
    if not -90 <= latitude <= 90:
        return None, None, "Latitude must be between -90 and 90."
    if not -180 <= longitude <= 180:
        return None, None, "Longitude must be between -180 and 180."
    return latitude, longitude, None


def register_account(account_number, homeowner_name, address, connection_type,
                     password, confirm_password, latitude=None, longitude=None):
    """Create a new resident account.

    Returns (success: bool, message: str, household_dict | None).
    """
    account_number = (account_number or "").strip().upper()
    homeowner_name = (homeowner_name or "").strip()
    address = (address or "").strip()
    connection_type = (connection_type or "").strip().capitalize()
    password = (password or "").strip()
    confirm_password = (confirm_password or "").strip()

    if not all([account_number, homeowner_name, address, connection_type]):
        return False, "All fields are required.", None
    if not ACCOUNT_PATTERN.fullmatch(account_number):
        return False, ("Account number must look like ACC-8011 "
                       "(ACC- followed by at least 4 digits)."), None
    if connection_type not in VALID_TYPES:
        return False, "Connection type must be Residential or Commercial.", None
    if len(password) < 6:
        return False, "Password must be at least 6 characters.", None
    if password != confirm_password:
        return False, "Passwords do not match.", None
    latitude, longitude, coordinate_error = parse_coordinate_pair(latitude, longitude)
    if coordinate_error:
        return False, coordinate_error, None

    try:
        with closing(get_connection()) as conn:
            existing = conn.execute("""
                SELECT 1
                FROM households
                WHERE UPPER(account_number) = UPPER(?)
            """, (account_number,)).fetchone()

            if existing:
                return (False,
                        "This account number already exists. Sign in to that "
                        "account or choose a new account number.",
                        None)

            with conn:
                cur = conn.execute("""
                    INSERT INTO households
                        (account_number, homeowner_name, address,
                         connection_type, latitude, longitude, password_hash)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (account_number, homeowner_name, address,
                      connection_type, latitude, longitude, hash_password(password)))
                new_id = cur.lastrowid
            log_audit_event("ACCOUNT_CREATED", account_number,
                            f"New account: {homeowner_name} at {address}")
            household = {
                "household_id": new_id,
                "account_number": account_number,
                "homeowner_name": homeowner_name,
                "address": address,
                "connection_type": connection_type,
                "status": "Active",
                "latitude": latitude,
                "longitude": longitude,
            }
            return True, "Account created. You're now signed in.", household
    except sqlite3.IntegrityError as e:
        if "UNIQUE" in str(e).upper():
            return (False,
                    "This account number already exists. Sign in to that "
                    "account or choose a new account number.",
                    None)
        return False, f"Invalid account details: {e}", None
    except sqlite3.Error as e:
        return False, f"Database error: {e}", None


# ---------------------------------------------------------------------------
# Audit log helper
# ---------------------------------------------------------------------------
def log_audit_event(action, target=None, details=None):
    try:
        with closing(get_connection()) as conn, conn:
            conn.execute("""
                INSERT INTO audit_logs (action, target, details)
                VALUES (?, ?, ?)
            """, (action, target, details))
    except sqlite3.Error as e:
        print(f"Audit log error: {e}")


# ---------------------------------------------------------------------------
# Writes — households
# ---------------------------------------------------------------------------
def insert_household(account_number, homeowner_name, address, connection_type,
                     status="Active", online_billing="No", password=None,
                     latitude=None, longitude=None):
    """Admin-created household. Password optional (unclaimed if None)."""
    account_number = (account_number or "").strip().upper()
    homeowner_name = (homeowner_name or "").strip()
    address = (address or "").strip()
    connection_type = (connection_type or "").strip().capitalize()
    status = (status or "Active").strip().capitalize()
    online_billing = (online_billing or "No").strip().capitalize()
    password = (password or "").strip() or None

    if not all([account_number, homeowner_name, address, connection_type]):
        return False, "All fields are required."
    if not ACCOUNT_PATTERN.fullmatch(account_number):
        return False, ("Account number must look like ACC-8011 "
                       "(ACC- followed by at least 4 digits).")
    if connection_type not in VALID_TYPES:
        return False, "Connection type must be Residential or Commercial."
    if status not in VALID_STATUSES:
        return False, f"Status must be one of: {', '.join(VALID_STATUSES)}."
    if online_billing not in ("Yes", "No"):
        return False, "Online billing must be 'Yes' or 'No'."
    if password and len(password) < 6:
        return False, "Password must be at least 6 characters."
    latitude, longitude, coordinate_error = parse_coordinate_pair(latitude, longitude)
    if coordinate_error:
        return False, coordinate_error

    password_hash = hash_password(password) if password else None

    try:
        with closing(get_connection()) as conn, conn:
            conn.execute("""
                INSERT INTO households
                    (account_number, homeowner_name, address,
                     connection_type, status, online_billing, latitude,
                     longitude, password_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (account_number, homeowner_name, address,
                  connection_type, status, online_billing, latitude,
                  longitude, password_hash))
    except sqlite3.IntegrityError as e:
        if "UNIQUE" in str(e).upper():
            return False, f"Account number {account_number} already exists."
        return False, f"Invalid data: {e}"
    except sqlite3.Error as e:
        return False, f"Database error: {e}"

    log_audit_event("INSERT_HOUSEHOLD", account_number,
                    f"Added {homeowner_name} at {address} ({connection_type})"
                    + (" [password set]" if password else " [unclaimed]"))
    return True, f"Household '{homeowner_name}' ({account_number}) added."


def delete_household(household_id):
    with closing(get_connection()) as conn:
        row = conn.execute("""
            SELECT account_number, homeowner_name
            FROM households WHERE household_id = ?
        """, (household_id,)).fetchone()
    if not row:
        return False, "Household not found."

    try:
        with closing(get_connection()) as conn, conn:
            conn.execute("DELETE FROM households WHERE household_id = ?",
                         (household_id,))
    except sqlite3.Error as e:
        return False, f"Database error: {e}"

    log_audit_event("DELETE_HOUSEHOLD", row["account_number"],
                    f"Deleted {row['homeowner_name']} "
                    f"(cascade removed all readings)")
    return True, (f"Household {row['account_number']} and its "
                  f"readings were deleted.")


# ---------------------------------------------------------------------------
# Writes — meter readings
# ---------------------------------------------------------------------------
def insert_meter_reading(household_id, billing_period, previous_reading,
                         current_reading, rate_per_kwh, reading_date):
    billing_period = (billing_period or "").strip()
    reading_date = (reading_date or "").strip()

    try:
        previous_reading = float(previous_reading)
        current_reading = float(current_reading)
        rate_per_kwh = float(rate_per_kwh)
    except (TypeError, ValueError):
        return False, "Readings and rate must be numbers."

    try:
        datetime.strptime(billing_period, "%Y-%m")
    except ValueError:
        return False, "Billing period must be YYYY-MM."
    try:
        reading_date_dt = datetime.strptime(reading_date, "%Y-%m-%d")
    except ValueError:
        return False, "Reading date must be YYYY-MM-DD."

    if reading_date_dt.strftime("%Y-%m") != billing_period:
        return False, (f"Reading date ({reading_date}) must fall within "
                       f"the billing period ({billing_period}).")

    if get_household_by_id(household_id) is None:
        return False, "That household does not exist."
    if previous_reading < 0:
        return False, "Previous reading cannot be negative."
    if current_reading < previous_reading:
        return False, (f"Current ({current_reading:,.1f}) cannot be lower "
                       f"than previous ({previous_reading:,.1f}).")
    if rate_per_kwh <= 0:
        return False, "Rate per kWh must be greater than zero."

    last = get_last_reading(household_id)
    if last is not None:
        last_period, last_current, _ = last
        if billing_period == last_period:
            return False, f"A reading for {billing_period} already exists."
        if (billing_period > last_period
                and abs(previous_reading - last_current) > 1e-6):
            return False, (f"Previous reading ({previous_reading:,.1f}) must "
                           f"match the last recorded value "
                           f"({last_current:,.1f}) from {last_period}.")

    try:
        with closing(get_connection()) as conn, conn:
            conn.execute("""
                INSERT INTO meter_readings
                    (household_id, billing_period, previous_reading,
                     current_reading, rate_per_kwh, reading_date, recorded_by)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (household_id, billing_period, previous_reading,
                  current_reading, rate_per_kwh, reading_date, "admin"))
    except sqlite3.IntegrityError as e:
        if "UNIQUE" in str(e).upper():
            return False, f"A reading for {billing_period} already exists."
        return False, f"Invalid data: {e}"
    except sqlite3.Error as e:
        return False, f"Database error: {e}"

    usage = current_reading - previous_reading
    log_audit_event("INSERT_READING", str(household_id),
                    f"Recorded {usage:,.1f} kWh for {billing_period}")
    return True, (f"Reading for {billing_period} saved: {usage:,.1f} kWh, "
                  f"estimated cost ₱{usage * rate_per_kwh:,.2f}.")


def delete_reading(reading_id):
    try:
        with closing(get_connection()) as conn, conn:
            cur = conn.execute(
                "DELETE FROM meter_readings WHERE reading_id = ?",
                (reading_id,)
            )
            if cur.rowcount == 0:
                return False, "Reading not found."
    except sqlite3.Error as e:
        return False, f"Database error: {e}"
    log_audit_event("DELETE_READING", str(reading_id),
                    f"Deleted reading {reading_id}")
    return True, "Reading deleted."


# ---------------------------------------------------------------------------
# Writes — payments
# ---------------------------------------------------------------------------
def record_payment(household_id, reading_id, amount_paid, gateway):
    """Record a payment against a specific reading. One per reading."""
    gateway = (gateway or "").strip()

    if gateway not in VALID_GATEWAYS:
        return False, f"Gateway must be one of: {', '.join(VALID_GATEWAYS)}."

    try:
        amount_paid = float(amount_paid)
    except (TypeError, ValueError):
        return False, "Amount must be a number."

    if amount_paid <= 0:
        return False, "Amount must be greater than zero."

    try:
        with closing(get_connection()) as conn:
            row = conn.execute("""
                SELECT r.reading_id, r.estimated_cost, r.billing_period,
                       r.household_id, h.account_number
                FROM meter_readings r
                JOIN households h ON h.household_id = r.household_id
                WHERE r.reading_id = ?
            """, (reading_id,)).fetchone()

            if row is None:
                return False, "That statement doesn't exist."
            if row["household_id"] != household_id:
                return False, "That statement doesn't belong to this household."
            if abs(amount_paid - row["estimated_cost"]) > 0.01:
                return False, (f"Amount must match the statement exactly: "
                               f"₱{row['estimated_cost']:,.2f}.")

            existing = conn.execute(
                "SELECT 1 FROM payments WHERE reading_id = ?", (reading_id,)
            ).fetchone()
            if existing:
                return False, "This statement is already paid."

            ref = f"{gateway[:3].upper()}-{secrets.token_hex(4).upper()}"

            with conn:
                conn.execute("""
                    INSERT INTO payments
                        (household_id, reading_id, amount_paid, gateway,
                         reference_no)
                    VALUES (?, ?, ?, ?, ?)
                """, (household_id, reading_id, amount_paid, gateway, ref))
    except sqlite3.Error as e:
        return False, f"Database error: {e}"

    log_audit_event(
        "ONLINE_PAYMENT", row["account_number"],
        f"Paid ₱{amount_paid:,.2f} for {row['billing_period']} "
        f"via {gateway} (ref {ref})"
    )
    return True, (f"Payment of ₱{amount_paid:,.2f} for "
                  f"{row['billing_period']} processed. Reference: {ref}")


# ---------------------------------------------------------------------------
# Writes — disaster incidents
# ---------------------------------------------------------------------------
def insert_disaster_incident(barangay, incident_type, severity_level,
                             date_reported):
    barangay = (barangay or "").strip()
    incident_type = (incident_type or "").strip()
    severity_level = (severity_level or "").strip().capitalize()
    date_reported = (date_reported or "").strip()

    if not barangay or not incident_type:
        return False, "Barangay and incident type are required."
    if severity_level not in ("High", "Medium", "Low"):
        return False, "Severity must be High, Medium, or Low."
    try:
        datetime.strptime(date_reported, "%Y-%m-%d")
    except ValueError:
        return False, "Date must be YYYY-MM-DD."

    try:
        with closing(get_connection()) as conn, conn:
            conn.execute("""
                INSERT INTO disaster_incidents
                    (barangay, incident_type, severity_level, date_reported)
                VALUES (?, ?, ?, ?)
            """, (barangay, incident_type, severity_level, date_reported))
    except sqlite3.Error as e:
        return False, f"Database error: {e}"

    log_audit_event("INSERT_DISASTER", barangay,
                    f"Logged {incident_type} ({severity_level}) "
                    f"on {date_reported}")
    return True, f"Disaster incident logged for {barangay}."
