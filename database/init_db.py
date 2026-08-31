import sys
import os
import json
import random
import argparse
from datetime import date, time, timedelta

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

# Allow importing from project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pymysql
from werkzeug.security import generate_password_hash


# ============================================================
# Config loader
# ============================================================

def load_config():
    try:
        from dotenv import load_dotenv
        load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))
    except ImportError:
        pass
    return {
        'host':    os.environ.get('DB_HOST', 'localhost'),
        'port':    int(os.environ.get('DB_PORT', 3306)),
        'user':    os.environ.get('DB_USER', 'root'),
        'password': os.environ.get('DB_PASSWORD', ''),
        'db_name': os.environ.get('DB_NAME', 'mediroute'),
    }


# ============================================================
# Seed Data Definitions
# ============================================================

SEED_USERS = [
    # name, email, role, doctor_id
    ('Admin User',          'admin@mediroute.lk',    'admin',    None),
    ('Emergency Operator',  'operator@mediroute.lk', 'operator', None),
    ('Dr. Pradeep Jayawardena', 'doctor@mediroute.lk', 'doctor', 1),
]
DEFAULT_PASSWORD = 'password123'


# id, name, latitude, longitude, type
SEED_LOCATIONS = [
    (1,  'Colombo Fort',                  6.9337,  79.8450, 'city'),
    (2,  'Colombo 7 - Cinnamon Gardens',  6.9147,  79.8637, 'hospital_area'),
    (3,  'Dehiwala',                      6.8516,  79.8653, 'city'),
    (4,  'Moratuwa',                      6.7728,  79.8858, 'city'),
    (5,  'Negombo',                       7.2086,  79.8358, 'city'),
    (6,  'Gampaha',                       7.0884,  79.9992, 'city'),
    (7,  'Kalutara',                      6.5854,  79.9607, 'city'),
    (8,  'Kandy',                         7.2906,  80.6337, 'city'),
    (9,  'Peradeniya',                    7.2682,  80.5964, 'city'),
    (10, 'Matale',                        7.4667,  80.6167, 'city'),
    (11, 'Kurunegala',                    7.4867,  80.3647, 'city'),
    (12, 'Kegalle',                       7.2530,  80.3464, 'city'),
    (13, 'Avissawella',                   6.9527,  80.2142, 'city'),
    (14, 'Ratnapura',                     6.6828,  80.3992, 'city'),
    (15, 'Embilipitiya',                  6.3414,  80.8453, 'city'),
    (16, 'Galle',                         6.0535,  80.2210, 'city'),
    (17, 'Matara',                        5.9549,  80.5550, 'city'),
    (18, 'Hambantota',                    6.1241,  81.1185, 'city'),
    (19, 'Badulla',                       6.9934,  81.0550, 'city'),
    (20, 'Nuwara Eliya',                  6.9497,  80.7891, 'city'),
    (21, 'Anuradhapura',                  8.3114,  80.4037, 'city'),
    (22, 'Polonnaruwa',                   7.9403,  81.0188, 'city'),
    (23, 'Habarana',                      8.0333,  80.7500, 'junction'),
    (24, 'Trincomalee',                   8.5874,  81.2152, 'city'),
    (25, 'Batticaloa',                    7.7170,  81.6924, 'city'),
    (26, 'Kalmunai',                      7.4145,  81.8217, 'city'),
    (27, 'Ampara',                        7.2985,  81.6731, 'city'),
    (28, 'Vavuniya',                      8.7514,  80.4983, 'city'),
    (29, 'Kilinochchi',                   9.3923,  80.3987, 'city'),
    (30, 'Jaffna',                        9.6615,  80.0255, 'city'),
    (31, 'Mannar',                        8.9791,  79.9042, 'city'),
    (32, 'Puttalam',                      8.0362,  79.8289, 'city'),
]

# id, name, location_id, capacity, avail_beds, icu, avail_icu, rating, status, wait_min
SEED_HOSPITALS = [
    (1, 'Hemas Hospital - Colombo (Main Branch)', 1, 150, 55, 20, 7, 4.9, 'active', 18),
    (2, 'Hemas Hospital - Thalawathugoda',         1, 100, 38, 14, 5, 4.7, 'active', 25),
    (3, 'Hemas Hospital - Wattala',               6, 130, 45, 18, 6, 4.8, 'active', 20),
    (4, 'Hemas Hospital - Galle',                16,  80, 28, 10, 4, 4.6, 'active', 22),
    (5, 'Hemas Hospital - Kandy',                 8,  90, 32, 12, 4, 4.5, 'active', 24),
    (6, 'Hemas Hospital - Kurunegala',           11,  75, 25,  8, 3, 4.4, 'active', 28),
]

# hospital_id, name, spec, rating, exp_years, availability
SEED_DOCTORS = [
    # Hemas Hospital - Colombo (Main Branch 1)
    (1, 'Dr. Pradeep Jayawardena',    'Cardiology',                  4.9, 18, 'available'),
    (1, 'Dr. Nimali Fernando',         'Neurology',                   4.8, 15, 'available'),
    (1, 'Dr. Ashan Perera',            'Emergency Medicine',          4.9, 12, 'available'),
    (1, 'Dr. Kumari Dissanayake',      'Pediatrics',                  4.7, 20, 'available'),
    (1, 'Dr. Thilak Weerasinghe',      'General Surgery',             4.6,  9, 'available'),
    (1, 'Dr. Sandya Rajapaksa',        'Obstetrics and Gynecology',  4.7, 14, 'available'),

    # Hemas Hospital - Thalawathugoda (Branch 2)
    (2, 'Dr. Chamara Rathnayake',      'Cardiology',                  4.7, 16, 'available'),
    (2, 'Dr. Sachini Kodagoda',        'Neurology',                   4.4, 10, 'available'),
    (2, 'Dr. Harsha Amarasinghe',      'Emergency Medicine',          4.8, 13, 'available'),
    (2, 'Dr. Mahesh Gunasekara',       'Internal Medicine',           4.5, 11, 'available'),
    (2, 'Dr. Ruwan Bandara',           'Orthopedics',                 4.6, 12, 'available'),
    (2, 'Dr. Dilani Wickramasinghe',   'Radiology',                   4.3,  8, 'available'),

    # Hemas Hospital - Wattala (Branch 3)
    (3, 'Dr. Nuwan Senanayake',        'General Surgery',             4.6, 17, 'available'),
    (3, 'Dr. Priya Samarawickrama',    'Internal Medicine',           4.4,  7, 'available'),
    (3, 'Dr. Lakshan Mendis',          'Orthopedics',                 4.5, 11, 'available'),
    (3, 'Dr. Chandana Samarasinghe',   'Emergency Medicine',          4.5, 14, 'available'),
    (3, 'Dr. Anura Liyanage',          'Radiology',                   4.2,  6, 'available'),
    (3, 'Dr. Roshani de Silva',        'Pediatrics',                  4.4,  8, 'available'),

    # Hemas Hospital - Galle (Branch 4)
    (4, 'Dr. Rajan Krishnan',          'Cardiology',                  4.6, 22, 'available'),
    (4, 'Dr. Kavitha Thayalan',        'Pediatrics',                  4.5, 14, 'available'),
    (4, 'Dr. Murali Sivapalan',        'General Surgery',             4.4, 12, 'available'),
    (4, 'Dr. Sumudu Perera',           'Internal Medicine',           4.3,  9, 'available'),
    (4, 'Dr. Tharanga Madanayake',     'Orthopedics',                 4.2,  5, 'available'),
    (4, 'Dr. Amara Wickrama',          'Neurology',                   4.5,  9, 'available'),

    # Hemas Hospital - Kandy (Branch 5)
    (5, 'Dr. Buddhika Ratnasiri',      'General Surgery',             4.5, 15, 'available'),
    (5, 'Dr. Nayana Dissanayake',      'Emergency Medicine',          4.6, 12, 'available'),
    (5, 'Dr. Malka Jayasinghe',        'Internal Medicine',           4.3, 10, 'available'),
    (5, 'Dr. Prasad Gunawardena',      'Cardiology',                  4.4, 13, 'available'),
    (5, 'Dr. Shivani Murugesan',       'Pediatrics',                  4.3, 14, 'available'),
    (5, 'Dr. Prabhath Silva',          'Orthopedics',                 4.2, 11, 'available'),

    # Hemas Hospital - Kurunegala (Branch 6)
    (6, 'Dr. Dimuth Liyanage',         'Cardiology',                  4.5, 14, 'available'),
    (6, 'Dr. Sunethra Perera',         'Emergency Medicine',          4.6, 11, 'available'),
    (6, 'Dr. Asela Gunaratne',         'General Surgery',             4.4, 10, 'available'),
    (6, 'Dr. Nadeeka Silva',           'Pediatrics',                  4.3,  8, 'available'),
    (6, 'Dr. Janaka Wickramasinghe',   'Internal Medicine',           4.2,  9, 'available'),
    (6, 'Dr. Chathura Bandara',        'Orthopedics',                 4.3,  7, 'available'),
]

# hospital_id, type, name, quantity, available_qty
SEED_RESOURCES = [
    # Hemas Colombo (Main Branch 1)
    (1, 'icu_bed', 'ICU Bed', 20, 7),
    (1, 'general_bed', 'General Ward Bed', 150, 55),
    (1, 'ventilator', 'Mechanical Ventilator', 15, 6),
    (1, 'cardiac_unit', 'Cardiac Care Unit', 10, 4),
    (1, 'ambulance', 'Emergency Ambulance', 5, 3),
    (1, 'room', 'Operating Theatre', 6, 3),
    (1, 'equipment', 'MRI / CT Scanner', 3, 3),
    (1, 'blood_bank', 'Blood Bank Unit', 1, 1),

    # Hemas Thalawathugoda (2)
    (2, 'icu_bed', 'ICU Bed', 14, 5),
    (2, 'general_bed', 'General Ward Bed', 100, 38),
    (2, 'ventilator', 'Mechanical Ventilator', 10, 4),
    (2, 'cardiac_unit', 'Cardiac Care Unit', 6, 2),
    (2, 'ambulance', 'Emergency Ambulance', 4, 2),
    (2, 'room', 'Operating Theatre', 4, 2),
    (2, 'equipment', 'MRI / CT Scanner', 2, 2),

    # Hemas Wattala (3)
    (3, 'icu_bed', 'ICU Bed', 18, 6),
    (3, 'general_bed', 'General Ward Bed', 130, 45),
    (3, 'ventilator', 'Mechanical Ventilator', 12, 5),
    (3, 'cardiac_unit', 'Cardiac Care Unit', 8, 3),
    (3, 'ambulance', 'Emergency Ambulance', 4, 2),
    (3, 'room', 'Operating Theatre', 4, 2),
    (3, 'blood_bank', 'Blood Bank Unit', 1, 1),

    # Hemas Galle (4)
    (4, 'icu_bed', 'ICU Bed', 10, 4),
    (4, 'general_bed', 'General Ward Bed', 80, 28),
    (4, 'ventilator', 'Mechanical Ventilator', 8, 3),
    (4, 'ambulance', 'Emergency Ambulance', 3, 2),
    (4, 'room', 'Operating Theatre', 3, 2),
    (4, 'blood_bank', 'Blood Bank Unit', 1, 1),

    # Hemas Kandy (5)
    (5, 'icu_bed', 'ICU Bed', 12, 4),
    (5, 'general_bed', 'General Ward Bed', 90, 32),
    (5, 'ventilator', 'Mechanical Ventilator', 8, 3),
    (5, 'cardiac_unit', 'Cardiac Care Unit', 4, 2),
    (5, 'ambulance', 'Emergency Ambulance', 3, 2),
    (5, 'room', 'Operating Theatre', 3, 2),

    # Hemas Kurunegala (6)
    (6, 'icu_bed', 'ICU Bed', 8, 3),
    (6, 'general_bed', 'General Ward Bed', 75, 25),
    (6, 'ventilator', 'Mechanical Ventilator', 6, 2),
    (6, 'ambulance', 'Emergency Ambulance', 3, 1),
    (6, 'room', 'Operating Theatre', 3, 2),
    (6, 'equipment', 'Digital X-Ray', 2, 2),
]

# src_loc_id, dst_loc_id, dist_km, travel_min, traffic, bidirectional
SEED_ROUTES = [
    # ---- Colombo metro area ----
    (1,  2,   3.0,   8,  'medium', True),
    (1,  3,   8.0,  20,  'medium', True),
    (2,  3,   5.0,  12,  'low',    True),
    (3,  4,  12.0,  20,  'low',    True),
    (4,  7,  22.0,  35,  'low',    True),
    # ---- Colombo to major cities ----
    (1,  5,  35.0,  50,  'medium', True),
    (1,  6,  30.0,  45,  'medium', True),
    (5,  6,  18.0,  30,  'low',    True),
    (1,  7,  42.0,  60,  'low',    True),
    (7, 16,  75.0,  90,  'low',    True),
    # ---- A1 Colombo – Kandy corridor ----
    (1, 12,  85.0, 120,  'medium', True),
    (12, 8,  40.0,  60,  'low',    True),
    (12,13,  38.0,  55,  'low',    True),
    (1, 13,  58.0,  90,  'low',    True),
    (13,14,  42.0,  60,  'low',    True),
    # ---- Kandy area ----
    (8,  9,  10.0,  15,  'low',    True),
    (8, 10,  25.0,  35,  'low',    True),
    (8, 11,  45.0,  65,  'low',    True),
    (9, 20,  68.0, 100,  'medium', True),
    (20,19,  66.0, 110,  'medium', True),
    # ---- Kurunegala / North-West ----
    (6, 11,  60.0,  80,  'low',    True),
    (11,32,  63.0,  90,  'low',    True),
    (5, 32,  65.0,  90,  'low',    True),
    (32,21,  95.0, 130,  'low',    True),
    # ---- South coast ----
    (16,17,  38.0,  55,  'low',    True),
    (17,18,  65.0,  90,  'low',    True),
    (14,15,  80.0, 120,  'low',    True),
    (15,18,  60.0,  90,  'low',    True),
    # ---- Anuradhapura connections ----
    (11,21,  90.0, 120,  'low',    True),
    (10,21, 135.0, 180,  'low',    True),
    (21,22, 100.0, 140,  'low',    True),
    (21,23,  80.0, 110,  'low',    True),
    (22,23,  25.0,  35,  'low',    True),
    (21,28,  82.0, 120,  'low',    True),
    # ---- Trincomalee corridor ----
    (23,24,  85.0, 120,  'low',    True),
    (22,24, 110.0, 160,  'low',    True),
    (24,25, 100.0, 145,  'low',    True),
    # ---- East coast ----
    (25,26,  40.0,  60,  'low',    True),
    (25,27,  60.0,  90,  'low',    True),
    (26,27,  30.0,  45,  'low',    True),
    (19,27, 100.0, 150,  'low',    True),
    # ---- North corridor (A9) ----
    (28,29,  72.0, 100,  'low',    True),
    (29,30,  62.0,  85,  'low',    True),
    (28,31, 120.0, 180,  'low',    True),
    (31,30, 160.0, 220,  'low',    True),
    (31,32, 150.0, 200,  'low',    True),
    # ---- Cross-island ----
    (22,25, 150.0, 220,  'low',    True),
    (15,27, 120.0, 180,  'low',    True),
    (18,27, 140.0, 200,  'low',    True),
    (1,  8, 116.0, 150,  'medium', True),   # Colombo–Kandy direct (A1 express)
    (8, 21, 132.0, 175,  'low',    True),   # Kandy–Anuradhapura
    (16,14,  95.0, 130,  'low',    True),   # Galle–Ratnapura
]

# ============================================================
# Patient name pools (Sri Lankan)
# ============================================================
MALE_FIRST = [
    'Nuwan','Kamal','Sunil','Chamara','Thilak','Mahesh','Dimuth','Asela',
    'Pradeep','Ruwan','Ashan','Harsha','Buddhika','Prasad','Tharaka',
    'Janaka','Sanjeewa','Roshan','Dilan','Lahiru','Kasun','Isuru',
    'Chanaka','Nimesh','Sanjaya','Yasith','Rajan','Murali','Prabhath','Kumara',
]
FEMALE_FIRST = [
    'Nilani','Kamala','Shanthi','Dilani','Chathu','Malshi','Nadeeka',
    'Sanduni','Hiruni','Sachini','Kumari','Priya','Kavitha','Shivani',
    'Nayana','Roshani','Malka','Sumudu','Dilkshi','Amara','Hashini',
    'Nethmi','Senali','Oshadi','Tharindi','Ridmi','Dulani','Minuri','Piyumi','Nadeesha',
]
SURNAMES = [
    'Perera','Fernando','Jayawardena','Bandara','Silva','Wickramasinghe',
    'Dissanayake','Rajapaksa','Gunawardena','Senanayake','Rathnayake',
    'Amarasinghe','Samarawickrama','Mendis','Liyanage','Gunasekara',
    'Weerasinghe','Ratnasiri','Samarasinghe','Kodagoda','Madanayake',
    'Jayasinghe','Wickrama','Murugesan','Krishnan','Thayalan','Sivapalan',
    'Pathirana','Karunarathna','Jayasekara',
]
BLOOD_TYPES   = ['A+','A-','B+','B-','AB+','AB-','O+','O-']
EMERGENCY_LVL = ['critical','high','medium','low']
EMERG_WEIGHTS = [0.10, 0.20, 0.40, 0.30]
SPECIALIZATIONS = [
    'Cardiology','Neurology','Orthopedics','Pediatrics',
    'Emergency Medicine','General Surgery','Internal Medicine',
    'Obstetrics and Gynecology','Radiology',None,None,None,  # Some patients have no required spec
]


def generate_patients(n: int = 100, seed: int = 42):
    rng = random.Random(seed)
    patients = []
    for i in range(1, n + 1):
        gender = rng.choice(['M', 'F'])
        first  = rng.choice(MALE_FIRST if gender == 'M' else FEMALE_FIRST)
        name   = f"{first} {rng.choice(SURNAMES)}"
        age    = rng.randint(5, 85)
        level  = rng.choices(EMERGENCY_LVL, weights=EMERG_WEIGHTS)[0]
        loc_id = rng.randint(1, 32)
        blood  = rng.choice(BLOOD_TYPES)
        spec   = rng.choice(SPECIALIZATIONS)
        phone  = f"077{rng.randint(1000000, 9999999)}"
        nic    = f"19{rng.randint(60, 99):02d}{rng.randint(10000000, 99999999)}"
        patients.append((name, nic, phone, age, gender, level, loc_id, blood, spec))
    return patients


def generate_appointments(n_patients: int, n: int = 100, seed: int = 42):
    rng   = random.Random(seed)
    base  = date(2025, 1, 1)
    appts = []
    for _ in range(n):
        p_id  = rng.randint(1, n_patients)
        d_id  = rng.randint(1, len(SEED_DOCTORS))
        # Map doctor -> hospital directly from SEED_DOCTORS definition
        h_id  = SEED_DOCTORS[d_id - 1][0]
        room  = f"Room {rng.randint(1,30):02d}"
        offset = rng.randint(0, 364)
        day   = base + timedelta(days=offset)
        hour  = rng.randint(8, 17)
        minute = rng.choice([0, 15, 30, 45])
        s_time = time(hour, minute)
        e_hour = hour + (1 if minute < 30 else 2)
        e_min  = (minute + 30) % 60
        e_time = time(min(e_hour, 18), e_min)
        status = rng.choice(['scheduled','completed','cancelled','pending'])
        appts.append((p_id, d_id, h_id, room, day, s_time, e_time, 30, status))
    return appts


def generate_resource_requests(n_patients: int, n: int = 20, seed: int = 99):
    rng = random.Random(seed)
    req_types = ['icu_bed','general_bed','ventilator','cardiac_unit','ambulance']
    reqs = []
    for _ in range(n):
        p_id   = rng.randint(1, n_patients)
        rtype  = rng.choice(req_types)
        prio   = rng.randint(1, 10)
        spec   = rng.choice(SPECIALIZATIONS[:8] + [None])
        h_pref = rng.randint(1, len(SEED_HOSPITALS))
        status = rng.choice(['pending','allocated','pending','pending'])  # mostly pending
        reqs.append((p_id, rtype, prio, spec, h_pref, status))
    return reqs


# ============================================================
# Database setup
# ============================================================

def get_connection(cfg, with_db: bool = True):
    kwargs = dict(
        host=cfg['host'],
        port=cfg['port'],
        user=cfg['user'],
        password=cfg['password'],
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True,
    )
    if with_db:
        kwargs['database'] = cfg['db_name']
    return pymysql.connect(**kwargs)


def create_database(cfg):
    print(f"  Creating database '{cfg['db_name']}' if not exists...")
    conn = get_connection(cfg, with_db=False)
    with conn.cursor() as cur:
        cur.execute(
            f"CREATE DATABASE IF NOT EXISTS `{cfg['db_name']}` "
            "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
        )
    conn.close()
    print("  ✓ Database ready.")


def run_schema(cfg, schema_path: str, drop_first: bool = True):
    print("  Running schema.sql...")
    conn = get_connection(cfg)
    schema_dir = os.path.dirname(schema_path)

    with open(schema_path, 'r', encoding='utf-8') as f:
        raw = f.read()

    # Split on semicolons, remove empty statements
    statements = [s.strip() for s in raw.split(';') if s.strip()]

    with conn.cursor() as cur:
        cur.execute("SET FOREIGN_KEY_CHECKS = 0")
        if drop_first:
            # Drop tables in reverse FK order
            tables = [
                'algorithm_results','emergency_requests','schedules',
                'resource_requests','appointments','routes',
                'patients','resources','doctors','hospitals',
                'users','locations',
            ]
            for tbl in tables:
                cur.execute(f"DROP TABLE IF EXISTS `{tbl}`")
            print("  ✓ Old tables dropped.")

        for stmt in statements:
            if stmt:
                cur.execute(stmt)

        cur.execute("SET FOREIGN_KEY_CHECKS = 1")

    conn.close()
    print("  ✓ Schema created.")


def seed_data(cfg):
    print("  Seeding data...")
    conn = get_connection(cfg)

    with conn.cursor() as cur:

        # ---- Users ----
        print("    Inserting users...")
        for name, email, role, doctor_id in SEED_USERS:
            pw = generate_password_hash(DEFAULT_PASSWORD)
            cur.execute(
                "INSERT IGNORE INTO users (name, email, password_hash, role, doctor_id) VALUES (%s,%s,%s,%s,%s)",
                (name, email, pw, role, doctor_id)
            )


        # ---- Locations ----
        print("    Inserting locations...")
        cur.executemany(
            "INSERT INTO locations (id,name,latitude,longitude,location_type) VALUES (%s,%s,%s,%s,%s)",
            SEED_LOCATIONS
        )

        # ---- Hospitals ----
        print("    Inserting hospitals...")
        cur.executemany(
            "INSERT INTO hospitals (id,name,location_id,capacity,available_beds,"
            "icu_beds,available_icu_beds,rating,status,avg_wait_time_min) VALUES "
            "(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            SEED_HOSPITALS
        )

        # ---- Doctors ----
        print("    Inserting doctors...")
        cur.executemany(
            "INSERT INTO doctors (hospital_id,name,specialization,rating,"
            "experience_years,availability_status) VALUES (%s,%s,%s,%s,%s,%s)",
            SEED_DOCTORS
        )

        # ---- Resources ----
        print("    Inserting resources...")
        for hosp_id, rtype, rname, qty, avail in SEED_RESOURCES:
            status = 'available' if avail > 0 else 'unavailable'
            if 0 < avail <= qty * 0.25:
                status = 'limited'
            cur.execute(
                "INSERT INTO resources (hospital_id,resource_type,resource_name,"
                "quantity,available_quantity,status) VALUES (%s,%s,%s,%s,%s,%s)",
                (hosp_id, rtype, rname, qty, avail, status)
            )

        # ---- Patients (100 synthetic) ----
        print("    Inserting 100 patients...")
        patients = generate_patients(100)
        cur.executemany(
            "INSERT INTO patients (name,nic,phone,age,gender,emergency_level,location_id,"
            "blood_type,required_specialization) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            patients
        )

        # ---- Routes ----
        print("    Inserting routes...")
        for src, dst, dist, tmin, traffic, bidir in SEED_ROUTES:
            cur.execute(
                "INSERT INTO routes (source_location_id,destination_location_id,"
                "distance_km,travel_time_min,traffic_level,is_bidirectional) "
                "VALUES (%s,%s,%s,%s,%s,%s)",
                (src, dst, dist, tmin, traffic, bidir)
            )

        # ---- Appointments (100 synthetic) ----
        print("    Inserting 100 appointments...")
        appts = generate_appointments(100, 100)
        cur.executemany(
            "INSERT INTO appointments (patient_id,doctor_id,hospital_id,room_number,"
            "appointment_date,start_time,end_time,duration_min,status) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            appts
        )

        # ---- Resource Requests ----
        print("    Inserting resource requests...")
        reqs = generate_resource_requests(100)
        cur.executemany(
            "INSERT INTO resource_requests (patient_id,resource_type,priority,"
            "required_specialization,preferred_hospital_id,status) "
            "VALUES (%s,%s,%s,%s,%s,%s)",
            reqs
        )

    conn.commit()
    conn.close()
    print("  ✓ All seed data inserted.")


# ============================================================
# Entry point
# ============================================================

def main():
    parser = argparse.ArgumentParser(description='MediRoute database initializer')
    parser.add_argument('--no-drop', action='store_true',
                        help='Skip dropping existing tables (add data only)')
    args = parser.parse_args()

    cfg = load_config()
    schema_path = os.path.join(os.path.dirname(__file__), 'schema.sql')

    print("\n=== MediRoute Database Init ===\n")
    print(f"  Host   : {cfg['host']}:{cfg['port']}")
    print(f"  DB     : {cfg['db_name']}")
    print(f"  User   : {cfg['user']}")
    print(f"  Schema : {schema_path}\n")

    try:
        create_database(cfg)
        run_schema(cfg, schema_path, drop_first=not args.no_drop)
        seed_data(cfg)

        print("\n✅ Database initialization complete!")
        print(f"\n   Seed credentials (all roles, password: '{DEFAULT_PASSWORD}'):")
        for item in SEED_USERS:
            name, email, role = item[0], item[1], item[2]
            print(f"     [{role:8s}]  {email}")
        print(f"\n   Run the app:  flask run")
        print(f"   Open browser: http://localhost:5000/login\n")

    except pymysql.OperationalError as e:
        print(f"\n❌ MySQL connection failed: {e}")
        print("   Check DB_HOST, DB_PORT, DB_USER, DB_PASSWORD in your .env file.")
        sys.exit(1)
    except FileNotFoundError:
        print(f"\n❌ schema.sql not found at: {schema_path}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
