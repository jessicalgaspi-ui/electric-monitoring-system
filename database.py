"""SQLite core for the merged Smart-Grid / Electricity Monitor system.

Combines:
  - the Streamlit rewrite's CHECK-constrained schema, GENERATED columns,
    portable BASE_DIR, and 6-month seed series, with
  - the teammate's extra tables (audit_logs, disaster_incidents) and
    geographical columns on households (latitude/longitude),
  - password-based authentication for residents (salted PBKDF2),
  - a payments table for tracking settled bills,
  - creation/update timestamps on households,
  - coordinate range validation, and provenance (recorded_by) on readings.

Tiered tariff lives as an analytical helper (tiered_cost) — the DB stores
flat-rate billing in the GENERATED estimated_cost column.

Run directly to (re)initialize:
    python database.py            # create schema + seed if empty
    python database.py --reset    # drop all tables and reseed
"""
import calendar
import hashlib
import os
import secrets
import sqlite3
import sys
from datetime import datetime, timedelta

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)
DB_NAME = os.path.join(DATA_DIR, "electricity_monitor.db")

# ---------------------------------------------------------------------------
# Rates & periods used by the billing engine (flat rate, stored per reading)
# ---------------------------------------------------------------------------
RATES = {
    "Residential": [11.50, 11.60, 11.75, 11.85, 11.90, 11.95],
    "Commercial":  [12.90, 13.00, 13.10, 13.20, 13.25, 13.30],
}
PERIODS = ["2026-04", "2026-05", "2026-06", "2026-07", "2026-08", "2026-09"]

# ---------------------------------------------------------------------------
# Tiered tariff — analytical only (never stored in the DB)
# ---------------------------------------------------------------------------
TIER_RATES = {
    "Residential": (9.20, 11.10, 13.50),
    "Commercial":  (10.50, 12.20, 14.80),
}
TIER_BOUNDS = (50.0, 200.0)  # lifeline ≤ 50, standard 51–200, peak > 200


def tiered_cost(consumption_kwh, connection_type="Residential"):
    """Compute the tiered tariff cost analytically (never stored)."""
    if consumption_kwh is None or consumption_kwh <= 0:
        return 0.0
    r1, r2, r3 = TIER_RATES.get(connection_type, TIER_RATES["Residential"])
    b1, b2 = TIER_BOUNDS
    if consumption_kwh <= b1:
        return consumption_kwh * r1
    if consumption_kwh <= b2:
        return b1 * r1 + (consumption_kwh - b1) * r2
    return b1 * r1 + (b2 - b1) * r2 + (consumption_kwh - b2) * r3


# ---------------------------------------------------------------------------
# Password hashing — salted PBKDF2-HMAC-SHA256
# ---------------------------------------------------------------------------
PBKDF2_ITERATIONS = 200_000


def hash_password(password: str) -> str:
    """Return a salted hash in the format '<salt>$<hex_digest>'.

    Two calls with the same password produce different outputs because
    the salt is randomly generated each time.
    """
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        PBKDF2_ITERATIONS,
    ).hex()
    return f"{salt}${digest}"


def verify_password(password: str, stored: str) -> bool:
    """Constant-time comparison against a stored hash.

    Handles both the new salted format ('<salt>$<digest>') and the legacy
    unsalted SHA-256 format for backward compatibility with pre-migration
    databases.
    """
    if not stored:
        return False

    if "$" in stored:
        salt, _, expected = stored.partition("$")
        digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            PBKDF2_ITERATIONS,
        ).hex()
        return secrets.compare_digest(digest, expected)

    legacy = hashlib.sha256(password.encode("utf-8")).hexdigest()
    return secrets.compare_digest(legacy, stored)


# ---------------------------------------------------------------------------
# Connection factory
# ---------------------------------------------------------------------------
def get_connection():
    """Shared factory. Row factory enables both index and key access."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------
def create_schema(conn):
    """Create every table and index if it does not already exist."""
    conn.execute("""
    CREATE TABLE IF NOT EXISTS households (
        household_id    INTEGER PRIMARY KEY AUTOINCREMENT,
        account_number  TEXT NOT NULL UNIQUE
                        CHECK (account_number GLOB 'ACC-[0-9][0-9][0-9][0-9]*'),
        homeowner_name  TEXT NOT NULL CHECK (length(trim(homeowner_name)) > 0),
        address         TEXT NOT NULL CHECK (length(trim(address)) > 0),
        connection_type TEXT NOT NULL
                        CHECK (connection_type IN ('Residential', 'Commercial')),
        status          TEXT NOT NULL DEFAULT 'Active'
                        CHECK (status IN ('Active', 'Inactive', 'Overdue',
                                          'Suspended', 'Disconnected')),
        online_billing  TEXT NOT NULL DEFAULT 'No'
                        CHECK (online_billing IN ('Yes', 'No')),
        latitude        REAL CHECK (latitude  IS NULL OR
                                    (latitude  BETWEEN -90  AND 90)),
        longitude       REAL CHECK (longitude IS NULL OR
                                    (longitude BETWEEN -180 AND 180)),
        password_hash   TEXT,
        created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at      DATETIME
    )
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS meter_readings (
        reading_id       INTEGER PRIMARY KEY AUTOINCREMENT,
        household_id     INTEGER NOT NULL,
        billing_period   TEXT NOT NULL
                         CHECK (billing_period GLOB '[0-9][0-9][0-9][0-9]-[0-1][0-9]'),
        previous_reading REAL NOT NULL CHECK (previous_reading >= 0),
        current_reading  REAL NOT NULL CHECK (current_reading >= previous_reading),
        consumption_kwh  REAL GENERATED ALWAYS AS
                         (current_reading - previous_reading) STORED,
        rate_per_kwh     REAL NOT NULL CHECK (rate_per_kwh > 0),
        estimated_cost   REAL GENERATED ALWAYS AS
                         ((current_reading - previous_reading) * rate_per_kwh) STORED,
        reading_date     TEXT NOT NULL
                         CHECK (reading_date GLOB '[0-9][0-9][0-9][0-9]-[0-1][0-9]-[0-3][0-9]'),
        recorded_by      TEXT NOT NULL DEFAULT 'admin',
        UNIQUE (household_id, billing_period),
        FOREIGN KEY (household_id) REFERENCES households (household_id) ON DELETE CASCADE
    )
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS audit_logs (
        log_id    INTEGER PRIMARY KEY AUTOINCREMENT,
        action    TEXT NOT NULL,
        target    TEXT,
        details   TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS disaster_incidents (
        incident_id    INTEGER PRIMARY KEY AUTOINCREMENT,
        barangay       TEXT NOT NULL CHECK (length(trim(barangay)) > 0),
        incident_type  TEXT NOT NULL,
        severity_level TEXT NOT NULL
                       CHECK (severity_level IN ('High', 'Medium', 'Low')),
        date_reported  TEXT NOT NULL
                       CHECK (date_reported GLOB '[0-9][0-9][0-9][0-9]-[0-1][0-9]-[0-3][0-9]')
    )
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS payments (
        payment_id   INTEGER PRIMARY KEY AUTOINCREMENT,
        household_id INTEGER NOT NULL,
        reading_id   INTEGER NOT NULL UNIQUE,
        amount_paid  REAL NOT NULL CHECK (amount_paid > 0),
        gateway      TEXT NOT NULL
                     CHECK (gateway IN ('GCash', 'Maya', 'Bank Transfer',
                                        'Cash', 'Manual')),
        reference_no TEXT UNIQUE,
        paid_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (household_id) REFERENCES households (household_id)
            ON DELETE CASCADE,
        FOREIGN KEY (reading_id)   REFERENCES meter_readings (reading_id)
            ON DELETE CASCADE
    )
    """)

    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_readings_household "
        "ON meter_readings (household_id)")
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_readings_period "
        "ON meter_readings (billing_period)")
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_audit_ts "
        "ON audit_logs (timestamp)")
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_payments_household "
        "ON payments (household_id)")
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_payments_reading "
        "ON payments (reading_id)")
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_households_account_number_ci "
        "ON households (UPPER(account_number))")
    conn.commit()


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------
def initialize_database():
    """Idempotent: creates missing tables and seeds only when empty."""
    conn = get_connection()
    try:
        create_schema(conn)
        if conn.execute("SELECT COUNT(*) FROM households").fetchone()[0] == 0:
            seed_expanded_data(conn)
        migrate_legacy_echague_coordinates(conn)
        migrate_synthetic_households_and_payments(conn)
        migrate_synthetic_household_names(conn)
    finally:
        conn.close()


def reset_database():
    """DEVELOPMENT ONLY: drops everything and reseeds.

    Drop order matters — payments references both households and
    meter_readings, so it must be dropped first.
    """
    conn = get_connection()
    try:
        for t in ("payments", "meter_readings", "households",
                  "audit_logs", "disaster_incidents"):
            conn.execute(f"DROP TABLE IF EXISTS {t};")
        conn.commit()
        create_schema(conn)
        seed_expanded_data(conn)
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Seed data
# ---------------------------------------------------------------------------
SEED_HOUSEHOLDS = [
    ("ACC-8001", "Maria Santos",
     "Brgy. Baluarte, Santiago City",  "Residential",  800.0, 28,
     [220, 240, 220, 230, 235, 225], 16.6850, 121.5520),
    ("ACC-8002", "Juan Dela Cruz",
     "Brgy. Echague Proper, Echague",  "Residential", 2600.0, 29,
     [250, 240, 230, 220, 260, 230], 16.7053600, 121.6749455),
    ("ACC-8003", "Roberto Gomez",
     "Brgy. San Fabian, Echague",      "Residential",  600.0, 30,
     [120, 120, 125, 120, 135, 125], 16.7136367, 121.6787365),
    ("ACC-8004", "Elena Reyes",
     "Brgy. Malitao, Echague",         "Commercial",  4500.0, 25,
     [600, 650, 700, 750, 830, 770], 16.6750119, 121.6594173),
    ("ACC-8005", "Carlos Aquino",
     "Brgy. Cabaruan, Santiago City",  "Residential", 1700.0, 30,
     [200, 190, 195, 190, 195, 205], 16.6900, 121.5500),
    ("ACC-8006", "Ana Marie Ramos",
     "Brgy. San Antonio, Echague",     "Residential",  900.0, 27,
     [180, 175, 185, 190, 200, 195], 16.6334427, 121.6400857),
    ("ACC-8007", "Ruel Pascual",
     "Brgy. Cabagan, Echague",         "Residential", 1500.0, 26,
     [150, 155, 160, 150, 165, 170], 16.7053600, 121.6749455),
    ("ACC-8008", "Greenfield Store",
     "Brgy. Alicia Road, Echague",     "Commercial",  3000.0, 24,
     [520, 540, 560, 580, 610, 590], 16.7053600, 121.6749455),
    ("ACC-8009", "Loida Villanueva",
     "Brgy. Dammang, Echague",         "Residential",  400.0, 28,
     [95, 100, 105, 110, 115, 108], 16.6895184, 121.6744432),
    ("ACC-8010", "Echague Mini-Mart",
     "Brgy. Centro, Echague",          "Commercial",  6200.0, 23,
     [700, 720, 740, 760, 800, 780], 16.7053600, 121.6749455),
]

LEGACY_ECHAGUE_COORDINATES = {
    "ACC-8002": (16.8545, 121.6720, 16.7053600, 121.6749455),
    "ACC-8003": (16.8420, 121.6610, 16.7136367, 121.6787365),
    "ACC-8004": (16.8610, 121.6830, 16.6750119, 121.6594173),
    "ACC-8006": (16.8350, 121.6500, 16.6334427, 121.6400857),
    "ACC-8007": (16.8200, 121.6400, 16.7053600, 121.6749455),
    "ACC-8008": (16.8300, 121.6550, 16.7053600, 121.6749455),
    "ACC-8009": (16.8450, 121.6650, 16.6895184, 121.6744432),
    "ACC-8010": (16.8533, 121.6708, 16.7053600, 121.6749455),
}


def migrate_legacy_echague_coordinates(conn):
    """Correct seeded demo pins only if they still have their original bad coordinates."""
    with conn:
        for account_number, coordinates in LEGACY_ECHAGUE_COORDINATES.items():
            old_latitude, old_longitude, latitude, longitude = coordinates
            conn.execute("""
                UPDATE households
                SET latitude = ?, longitude = ?, updated_at = CURRENT_TIMESTAMP
                WHERE account_number = ?
                  AND address LIKE '%Echague%'
                  AND latitude = ? AND longitude = ?
            """, (latitude, longitude, account_number, old_latitude, old_longitude))


SEED_DISASTERS = [
    ("Baluarte, Santiago City", "Typhoon Ramil Wind Gusts",     "High",   "2026-04-15"),
    ("Echague Proper, Echague", "Localized Flooding",           "Medium", "2026-05-04"),
    ("San Fabian, Echague",     "Feeder Line Lightning Strike", "High",   "2026-06-18"),
    ("Malitao, Echague",        "Transformer Overload",         "Medium", "2026-07-22"),
    ("Cabaruan, Santiago City", "Severe Thunderstorm Outage",   "High",   "2026-08-10"),
    ("San Antonio, Echague",    "Downed Power Line",            "High",   "2026-06-02"),
]

SYNTHETIC_LOCATIONS = [
    ("Brgy. Echague Proper, Echague", 16.7053600, 121.6749455),
    ("Brgy. San Fabian, Echague", 16.7136367, 121.6787365),
    ("Brgy. Malitao, Echague", 16.6750119, 121.6594173),
    ("Brgy. San Antonio, Echague", 16.6334427, 121.6400857),
    ("Brgy. Dammang, Echague", 16.6895184, 121.6744432),
    ("Brgy. Baluarte, Santiago City", 16.6661277, 121.5535092),
]

SYNTHETIC_STATUSES = [
    "Active", "Active", "Active", "Overdue", "Active",
    "Active", "Overdue", "Inactive", "Active", "Suspended",
    "Active", "Overdue", "Active", "Inactive", "Overdue",
    "Suspended", "Active", "Disconnected", "Disconnected",
]

SYNTHETIC_TYPES = [
    "Residential", "Residential", "Commercial", "Residential", "Residential",
    "Residential", "Commercial", "Residential", "Residential", "Commercial",
    "Residential", "Residential", "Commercial", "Residential", "Residential",
    "Residential", "Commercial", "Residential", "Commercial",
]

SYNTHETIC_HOMEOWNER_NAMES = [
    "Clarissa Mendoza", "Ramon Villanueva", "Domingo Family Store",
    "Tomas Agustin", "Maribel Dizon", "Noel Ramos",
    "Bautista Rice & Feeds", "Arvin Manalo", "Jocelyn Garcia",
    "Valdez General Merchandise", "Teresa Navarro", "Danilo Cruz",
    "Castillo Farm Supply", "Joel Santiago", "Grace Maturan",
    "Victor Domingo", "Reyes Family Grocery", "Junel Pascual",
    "Aquino Mini Mart",
]

PREVIOUS_SYNTHETIC_HOMEOWNER_NAMES = [
    "Clarissa Mendoza", "Ramon Villanueva", "Liza Domingo",
    "Tomas Agustin", "Maribel Dizon", "Noel Ramos",
    "Felisa Bautista", "Arvin Manalo", "Jocelyn Garcia",
    "Edwin Valdez", "Teresa Navarro", "Danilo Cruz",
    "Rowena Castillo", "Joel Santiago", "Grace Maturan",
    "Victor Domingo", "Alma Reyes", "Junel Pascual",
    "Celine Aquino",
]


def _build_readings(household_id, ctype, start_reading, base_day, consumptions):
    rows = []
    previous = start_reading
    for period, kwh, rate in zip(PERIODS, consumptions, RATES[ctype]):
        year, month = int(period[:4]), int(period[5:])
        day = min(base_day, calendar.monthrange(year, month)[1])
        current = previous + kwh
        rows.append((household_id, period, previous, current,
                     rate, f"{period}-{day:02d}"))
        previous = current
    return rows


def migrate_synthetic_households_and_payments(conn):
    """Add demo households and histories once, without replacing existing data."""
    demo_hash = conn.execute("""
        SELECT password_hash
        FROM households
        WHERE CAST(SUBSTR(account_number, 5) AS INTEGER) BETWEEN 8001 AND 8010
          AND password_hash IS NOT NULL
        ORDER BY account_number
        LIMIT 1
    """).fetchone()

    if demo_hash is None:
        print("Synthetic demo accounts not added: provision a demo account password first.")

    with conn:
        if demo_hash is not None:
            for index in range(19):
                account_number = f"ACC-{8012 + index}"
                exists = conn.execute("""
                    SELECT 1 FROM households WHERE UPPER(account_number) = UPPER(?)
                """, (account_number,)).fetchone()
                if exists:
                    continue

                address, latitude, longitude = SYNTHETIC_LOCATIONS[index % len(SYNTHETIC_LOCATIONS)]
                connection_type = SYNTHETIC_TYPES[index]
                status = SYNTHETIC_STATUSES[index]
                homeowner_name = SYNTHETIC_HOMEOWNER_NAMES[index]
                cur = conn.execute("""
                    INSERT INTO households
                        (account_number, homeowner_name, address, connection_type,
                         status, online_billing, latitude, longitude, password_hash)
                    VALUES (?, ?, ?, ?, ?, 'Yes', ?, ?, ?)
                """, (account_number, homeowner_name, address, connection_type,
                      status, latitude, longitude, demo_hash["password_hash"]))
                household_id = cur.lastrowid

                baseline = (90 + (index * 37) % 190 if connection_type == "Residential"
                            else 360 + (index * 83) % 520)
                consumptions = [
                    baseline + ((index * 13 + month * 17) % 61) - 30
                    for month in range(6)
                ]
                start_reading = 400 + index * 613
                base_day = 18 + index % 12
                readings = _build_readings(
                    household_id, connection_type, start_reading,
                    base_day, consumptions,
                )
                conn.executemany("""
                    INSERT INTO meter_readings
                        (household_id, billing_period, previous_reading,
                         current_reading, rate_per_kwh, reading_date)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, readings)

        gateways = ("GCash", "Maya", "Bank Transfer", "Cash", "Manual")
        for household in conn.execute("""
            SELECT household_id, account_number, status, connection_type
            FROM households ORDER BY household_id
        """).fetchall():
            paid_count = conn.execute("""
                SELECT COUNT(*) FROM payments WHERE household_id = ?
            """, (household["household_id"],)).fetchone()[0]
            if paid_count:
                continue

            statements = conn.execute("""
                SELECT r.reading_id, r.billing_period, r.estimated_cost, r.reading_date
                FROM meter_readings r
                WHERE r.household_id = ?
                ORDER BY r.billing_period
            """, (household["household_id"],)).fetchall()
            if not statements:
                index = household["household_id"]
                connection_type = household["connection_type"]
                baseline = (90 + (index * 37) % 190 if connection_type == "Residential"
                            else 360 + (index * 83) % 520)
                consumptions = [
                    baseline + ((index * 13 + month * 17) % 61) - 30
                    for month in range(6)
                ]
                readings = _build_readings(
                    index, connection_type, 400 + index * 613,
                    18 + index % 12, consumptions,
                )
                conn.executemany("""
                    INSERT INTO meter_readings
                        (household_id, billing_period, previous_reading,
                         current_reading, rate_per_kwh, reading_date)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, readings)
                statements = conn.execute("""
                    SELECT r.reading_id, r.billing_period, r.estimated_cost, r.reading_date
                    FROM meter_readings r
                    WHERE r.household_id = ?
                    ORDER BY r.billing_period
                """, (index,)).fetchall()

            status_payment_count = {
                "Active": 2 + household["household_id"] % 5,
                "Overdue": 2,
                "Inactive": 3,
                "Suspended": 1,
                "Disconnected": 1,
            }
            count = min(status_payment_count.get(household["status"], 2), len(statements))
            for index, statement in enumerate(statements[:count]):
                paid_at = (datetime.strptime(statement["reading_date"], "%Y-%m-%d")
                           + timedelta(days=3)).strftime("%Y-%m-%d %H:%M:%S")
                reference = f"SYN-{household['account_number']}-{statement['billing_period']}"
                conn.execute("""
                    INSERT INTO payments
                        (household_id, reading_id, amount_paid, gateway,
                         reference_no, paid_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (household["household_id"], statement["reading_id"],
                      statement["estimated_cost"],
                      gateways[(household["household_id"] + index) % len(gateways)],
                      reference, paid_at))


def migrate_synthetic_household_names(conn):
    """Set person names for homes and business names for synthetic commercial accounts."""
    with conn:
        for index, homeowner_name in enumerate(SYNTHETIC_HOMEOWNER_NAMES):
            conn.execute("""
                UPDATE households
                SET homeowner_name = ?, updated_at = CURRENT_TIMESTAMP
                WHERE account_number = ?
                  AND homeowner_name IN (?, ?)
            """, (
                homeowner_name,
                f"ACC-{8012 + index}",
                PREVIOUS_SYNTHETIC_HOMEOWNER_NAMES[index],
                f"Synthetic {'Shop' if SYNTHETIC_TYPES[index] == 'Commercial' else 'Household'} {8012 + index}",
            ))


def seed_expanded_data(conn):
    """Seeds 10 unclaimed households + 60 readings + 6 disasters + 1 audit log."""
    with conn:
        conn.executemany("""
            INSERT INTO households
                (account_number, homeowner_name, address, connection_type,
                 latitude, longitude)
            VALUES (?, ?, ?, ?, ?, ?)
        """, [(h[0], h[1], h[2], h[3], h[7], h[8]) for h in SEED_HOUSEHOLDS])

        readings = []
        for hid, h in enumerate(SEED_HOUSEHOLDS, start=1):
            _, _, _, ctype, start_reading, base_day, consumptions, _, _ = h
            readings.extend(_build_readings(hid, ctype, start_reading,
                                            base_day, consumptions))
        conn.executemany("""
            INSERT INTO meter_readings
                (household_id, billing_period, previous_reading, current_reading,
                 rate_per_kwh, reading_date)
            VALUES (?, ?, ?, ?, ?, ?)
        """, readings)

        conn.executemany("""
            INSERT INTO disaster_incidents
                (barangay, incident_type, severity_level, date_reported)
            VALUES (?, ?, ?, ?)
        """, SEED_DISASTERS)

        conn.execute("""
            INSERT INTO audit_logs (action, target, details)
            VALUES ('SYSTEM_INIT', 'SYSTEM',
                    'Database seeded with 10 unclaimed households, 60 readings, 6 disasters.')
        """)


if __name__ == "__main__":
    if "--reset" in sys.argv:
        reset_database()
        print(f"Database reset and re-seeded at:\n  {DB_NAME}")
    else:
        initialize_database()
        print(f"Database initialized (existing data preserved):\n  {DB_NAME}")
