"""SQLite persistence and role-scoped access for Vetted."""

from __future__ import annotations

import hashlib
import hmac
import os
import re
import secrets
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from data import DEMO_CLIENTS, QUESTIONS
from scoring import POINTS, calculate_deal_score


APP_DIR = Path(__file__).resolve().parent
DB_PATH = Path(os.environ.get("VETTED_DB_PATH", APP_DIR / "instance" / "vetted.sqlite3"))
SCHEMA_PATH = APP_DIR / "schema.sql"
HASH_ITERATIONS = 260_000


@contextmanager
def connection(path: Path = DB_PATH) -> Iterator[sqlite3.Connection]:
    db = sqlite3.connect(path, timeout=10)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, HASH_ITERATIONS)
    return f"pbkdf2_sha256${HASH_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algorithm, count, salt_hex, digest_hex = stored.split("$")
        if algorithm != "pbkdf2_sha256":
            return False
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), int(count))
        return hmac.compare_digest(actual, bytes.fromhex(digest_hex))
    except (TypeError, ValueError):
        return False


def init_db(path: Path = DB_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with connection(path) as db:
        db.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        # Streamlit can start more than one session at once. Serialize schema
        # inspection and migrations so two sessions cannot add the same column.
        db.execute("BEGIN IMMEDIATE")
        columns = {row["name"] for row in db.execute("PRAGMA table_info(advisor_users)")}
        if "username" not in columns:
            db.execute("ALTER TABLE advisor_users ADD COLUMN username TEXT")
        db.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_advisor_username ON advisor_users(username)")
        client_columns = {row["name"] for row in db.execute("PRAGMA table_info(clients)")}
        if "ebitda" not in client_columns:
            db.execute("ALTER TABLE clients ADD COLUMN ebitda INTEGER")
        if "employee_count" not in client_columns:
            db.execute(
                "ALTER TABLE clients ADD COLUMN employee_count INTEGER "
                "CHECK (employee_count >= 0)"
            )
        if db.execute("SELECT COUNT(*) FROM firms").fetchone()[0] == 0:
            _seed_demo(db)
        if db.execute("PRAGMA user_version").fetchone()[0] < 1:
            _migrate_demo_credentials(db)
            db.execute("PRAGMA user_version = 1")
        if db.execute("PRAGMA user_version").fetchone()[0] < 2:
            _migrate_business_profile(db)
            db.execute("PRAGMA user_version = 2")


def _seed_demo(db: sqlite3.Connection) -> None:
    firm_id = db.execute(
        "INSERT INTO firms (name) VALUES (?)", ("Vetted Advisory Partners",)
    ).lastrowid
    advisor_id = db.execute(
        "INSERT INTO advisor_users (firm_id, username, email, display_name, password_hash) VALUES (?, ?, ?, ?, ?)",
        (firm_id, "admin", "admin@vetted.local", "Administrator", hash_password("admin")),
    ).lastrowid

    option_ids: dict[tuple[str, str], tuple[int, int]] = {}
    for order, question in enumerate(QUESTIONS, start=1):
        question_id = db.execute(
            "INSERT INTO questions (field_key, prompt, display_order) VALUES (?, ?, ?)",
            (question["key"], question["prompt"], order),
        ).lastrowid
        for rating in ("high", "medium", "low"):
            option_id = db.execute(
                "INSERT INTO answer_options (question_id, rating, answer_text, points) VALUES (?, ?, ?, ?)",
                (question_id, rating, question[rating], POINTS[rating]),
            ).lastrowid
            option_ids[(question["key"], rating)] = (question_id, option_id)

    for client in DEMO_CLIENTS:
        client_id = db.execute(
            "INSERT INTO clients "
            "(firm_id, business_name, industry, annual_revenue, ebitda, employee_count) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                firm_id, client["name"], client["industry"], client["annual_revenue"],
                client["ebitda"], client["employee_count"],
            ),
        ).lastrowid
        # Sample records appear in the advisor pipeline; their owner accounts are
        # intentionally not shared as public demo credentials.
        db.execute(
            "INSERT INTO business_users (client_id, email, display_name, password_hash) VALUES (?, ?, ?, ?)",
            (client_id, client["owner_email"], client["owner_name"], hash_password(secrets.token_urlsafe(24))),
        )
        for question, rating in zip(QUESTIONS, client["ratings"], strict=True):
            question_id, option_id = option_ids[(question["key"], rating)]
            db.execute(
                "INSERT INTO questionnaire_responses (client_id, question_id, option_id) VALUES (?, ?, ?)",
                (client_id, question_id, option_id),
            )
        if client["decision"]:
            db.execute(
                "INSERT INTO advisor_decisions (client_id, advisor_user_id, decision, note) VALUES (?, ?, ?, ?)",
                (client_id, advisor_id, client["decision"], "Preloaded sample decision."),
            )


def _migrate_demo_credentials(db: sqlite3.Connection) -> None:
    """Upgrade a database made by the earlier classroom demo in place."""
    old_admin = db.execute(
        "SELECT id FROM advisor_users WHERE email = ?", ("advisor@vetted.demo",)
    ).fetchone()
    if old_admin:
        db.execute(
            "UPDATE advisor_users SET username = ?, email = ?, display_name = ?, password_hash = ? WHERE id = ?",
            ("admin", "admin@vetted.local", "Administrator", hash_password("admin"), old_admin["id"]),
        )
    elif not db.execute("SELECT 1 FROM advisor_users WHERE username = 'admin'").fetchone():
        firm_id = db.execute("SELECT id FROM firms ORDER BY id LIMIT 1").fetchone()[0]
        db.execute(
            "INSERT INTO advisor_users (firm_id, username, email, display_name, password_hash) VALUES (?, ?, ?, ?, ?)",
            (firm_id, "admin", "admin@vetted.local", "Administrator", hash_password("admin")),
        )
    for row in db.execute("SELECT id FROM business_users WHERE email LIKE '%@vetted.demo'").fetchall():
        db.execute(
            "UPDATE business_users SET password_hash = ? WHERE id = ?",
            (hash_password(secrets.token_urlsafe(24)), row["id"]),
        )


def _migrate_business_profile(db: sqlite3.Connection) -> None:
    """Backfill profile details for the three existing fictional clients."""
    for client in DEMO_CLIENTS:
        db.execute(
            "UPDATE clients SET ebitda = ?, employee_count = ? "
            "WHERE id = (SELECT client_id FROM business_users WHERE email = ?)",
            (client["ebitda"], client["employee_count"], client["owner_email"]),
        )


def authenticate_advisor(username: str, password: str, path: Path = DB_PATH) -> dict | None:
    with connection(path) as db:
        row = db.execute(
            "SELECT id, firm_id, username, display_name, password_hash FROM advisor_users WHERE username = ?",
            (username.strip(),),
        ).fetchone()
    if not row or not verify_password(password, row["password_hash"]):
        return None
    return {key: row[key] for key in ("id", "firm_id", "username", "display_name")}


def authenticate_business(email: str, password: str, path: Path = DB_PATH) -> dict | None:
    with connection(path) as db:
        row = db.execute(
            "SELECT id, client_id, email, display_name, password_hash FROM business_users WHERE email = ?",
            (email.strip(),),
        ).fetchone()
    if not row or not verify_password(password, row["password_hash"]):
        return None
    return {key: row[key] for key in ("id", "client_id", "email", "display_name")}


def create_business_account(
    *,
    owner_name: str,
    email: str,
    password: str,
    business_name: str,
    industry: str,
    annual_revenue: int,
    ebitda: int,
    employee_count: int,
    path: Path = DB_PATH,
) -> dict:
    owner_name, email = owner_name.strip(), email.strip().lower()
    business_name, industry = business_name.strip(), industry.strip()
    if len(owner_name) < 2 or len(business_name) < 2 or not industry:
        raise ValueError("Enter your name, business name, and industry.")
    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
        raise ValueError("Enter a valid email address.")
    if len(password) < 8:
        raise ValueError("Password must contain at least 8 characters.")
    if not isinstance(annual_revenue, int) or annual_revenue < 0:
        raise ValueError("Annual revenue must be zero or greater.")
    if not isinstance(ebitda, int):
        raise ValueError("Enter EBITDA in whole US dollars.")
    if not isinstance(employee_count, int) or employee_count < 0:
        raise ValueError("Number of employees must be zero or greater.")
    with connection(path) as db:
        firm = db.execute("SELECT id FROM firms ORDER BY id LIMIT 1").fetchone()
        if not firm:
            raise RuntimeError("Advisor firm has not been initialized")
        if db.execute("SELECT 1 FROM business_users WHERE email = ?", (email,)).fetchone():
            raise ValueError("An account with this email already exists.")
        client_id = db.execute(
            "INSERT INTO clients "
            "(firm_id, business_name, industry, annual_revenue, ebitda, employee_count) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (firm["id"], business_name, industry, annual_revenue, ebitda, employee_count),
        ).lastrowid
        try:
            user_id = db.execute(
                "INSERT INTO business_users (client_id, email, display_name, password_hash) VALUES (?, ?, ?, ?)",
                (client_id, email, owner_name, hash_password(password)),
            ).lastrowid
        except sqlite3.IntegrityError as exc:
            raise ValueError("An account with this email already exists.") from exc
    return {"id": user_id, "client_id": client_id, "email": email, "display_name": owner_name}


def questionnaire_questions(path: Path = DB_PATH) -> list[dict]:
    with connection(path) as db:
        questions = db.execute(
            "SELECT id, field_key, prompt, display_order FROM questions ORDER BY display_order"
        ).fetchall()
        result = []
        for question in questions:
            options = db.execute(
                "SELECT rating, answer_text FROM answer_options WHERE question_id = ?",
                (question["id"],),
            ).fetchall()
            item = dict(question)
            item["options"] = {row["rating"]: row["answer_text"] for row in options}
            result.append(item)
        return result


def submit_business_questionnaire(
    business_user_id: int, ratings: dict[str, str], path: Path = DB_PATH
) -> int:
    score = calculate_deal_score(ratings)
    with connection(path) as db:
        owner = db.execute(
            "SELECT client_id FROM business_users WHERE id = ?", (business_user_id,)
        ).fetchone()
        if not owner:
            raise PermissionError("Business account not found")
        client_id = owner["client_id"]
        if db.execute(
            "SELECT 1 FROM questionnaire_responses WHERE client_id = ? LIMIT 1", (client_id,)
        ).fetchone():
            raise ValueError("This questionnaire has already been submitted.")
        for field_key, rating in ratings.items():
            option = db.execute(
                """
                SELECT q.id AS question_id, a.id AS option_id
                FROM questions AS q JOIN answer_options AS a ON a.question_id = q.id
                WHERE q.field_key = ? AND a.rating = ?
                """,
                (field_key, rating),
            ).fetchone()
            if not option:
                raise ValueError(f"Unknown answer for {field_key}")
            db.execute(
                "INSERT INTO questionnaire_responses (client_id, question_id, option_id) VALUES (?, ?, ?)",
                (client_id, option["question_id"], option["option_id"]),
            )
    return score


def _responses(db: sqlite3.Connection, client_id: int) -> list[dict]:
    rows = db.execute(
        """
        SELECT q.display_order, q.field_key, q.prompt, a.rating, a.answer_text, a.points
        FROM questionnaire_responses AS r
        JOIN questions AS q ON q.id = r.question_id
        JOIN answer_options AS a ON a.id = r.option_id AND a.question_id = r.question_id
        WHERE r.client_id = ? ORDER BY q.display_order
        """,
        (client_id,),
    ).fetchall()
    return [dict(row) for row in rows]


def _latest_decision(db: sqlite3.Connection, client_id: int) -> dict | None:
    row = db.execute(
        """
        SELECT d.decision, d.note, d.decided_at, a.display_name AS advisor_name
        FROM advisor_decisions AS d JOIN advisor_users AS a ON a.id = d.advisor_user_id
        WHERE d.client_id = ? ORDER BY d.id DESC LIMIT 1
        """,
        (client_id,),
    ).fetchone()
    return dict(row) if row else None


def _client_record(db: sqlite3.Connection, client_id: int, firm_id: int | None = None) -> dict | None:
    if firm_id is None:
        row = db.execute("SELECT * FROM clients WHERE id = ?", (client_id,)).fetchone()
    else:
        row = db.execute(
            "SELECT * FROM clients WHERE id = ? AND firm_id = ?", (client_id, firm_id)
        ).fetchone()
    if not row:
        return None
    client = dict(row)
    client["responses"] = _responses(db, client_id)
    client["submitted"] = len(client["responses"]) == len(QUESTIONS)
    client["score"] = (
        calculate_deal_score({r["field_key"]: r["rating"] for r in client["responses"]})
        if client["submitted"] else None
    )
    client["latest_decision"] = _latest_decision(db, client_id)
    return client


def list_advisor_clients(firm_id: int, path: Path = DB_PATH) -> list[dict]:
    with connection(path) as db:
        rows = db.execute(
            "SELECT id FROM clients WHERE firm_id = ? ORDER BY business_name", (firm_id,)
        ).fetchall()
        return [_client_record(db, row["id"], firm_id) for row in rows]


def get_advisor_client(client_id: int, firm_id: int, path: Path = DB_PATH) -> dict | None:
    with connection(path) as db:
        return _client_record(db, client_id, firm_id)


def get_business_client(business_user_id: int, path: Path = DB_PATH) -> dict | None:
    with connection(path) as db:
        row = db.execute(
            "SELECT client_id FROM business_users WHERE id = ?", (business_user_id,)
        ).fetchone()
        return _client_record(db, row["client_id"]) if row else None


def decision_history(client_id: int, firm_id: int, path: Path = DB_PATH) -> list[dict]:
    with connection(path) as db:
        if not db.execute(
            "SELECT 1 FROM clients WHERE id = ? AND firm_id = ?", (client_id, firm_id)
        ).fetchone():
            raise PermissionError("Client does not belong to this advisor firm")
        rows = db.execute(
            """
            SELECT d.decision, d.note, d.decided_at, a.display_name AS advisor_name
            FROM advisor_decisions AS d JOIN advisor_users AS a ON a.id = d.advisor_user_id
            WHERE d.client_id = ? ORDER BY d.id DESC
            """,
            (client_id,),
        ).fetchall()
        return [dict(row) for row in rows]


def record_decision(
    client_id: int,
    advisor_user_id: int,
    firm_id: int,
    decision: str,
    note: str = "",
    path: Path = DB_PATH,
) -> None:
    if decision not in {"accepted", "rejected", "clarification"}:
        raise ValueError("Invalid decision")
    with connection(path) as db:
        client = db.execute(
            "SELECT 1 FROM clients WHERE id = ? AND firm_id = ?", (client_id, firm_id)
        ).fetchone()
        advisor = db.execute(
            "SELECT 1 FROM advisor_users WHERE id = ? AND firm_id = ?", (advisor_user_id, firm_id)
        ).fetchone()
        count = db.execute(
            "SELECT COUNT(*) FROM questionnaire_responses WHERE client_id = ?", (client_id,)
        ).fetchone()[0]
        if not client or not advisor:
            raise PermissionError("Advisor is not authorized for this client")
        if count != len(QUESTIONS):
            raise ValueError("Complete questionnaire required before an advisor decision")
        db.execute(
            "INSERT INTO advisor_decisions (client_id, advisor_user_id, decision, note) VALUES (?, ?, ?, ?)",
            (client_id, advisor_user_id, decision, note.strip()[:1000]),
        )
