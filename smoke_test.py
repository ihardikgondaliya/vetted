"""Check routes, signup, questionnaire submission, and SQLite persistence."""

import os
import tempfile
from pathlib import Path

from streamlit.testing.v1 import AppTest


with tempfile.TemporaryDirectory() as temp_dir:
    os.environ["VETTED_DB_PATH"] = str(Path(temp_dir) / "vetted-test.sqlite3")

    from database import (  # imported after setting the isolated database path
        authenticate_advisor,
        authenticate_business,
        connection,
        create_business_account,
        get_advisor_client,
        get_business_client,
        init_db,
        list_advisor_clients,
        record_decision,
    )

    init_db()
    admin = authenticate_advisor("admin", "admin")
    assert admin is not None
    assert authenticate_advisor("advisor@vetted.demo", "VettedDemo123!") is None
    assert authenticate_advisor("admin", "wrong") is None
    assert authenticate_business("northstar@vetted.demo", "VettedDemo123!") is None
    clients = list_advisor_clients(admin["firm_id"])
    assert sorted(client["score"] for client in clients) == [15, 60, 90]
    with connection() as db:
        assert db.execute("SELECT COUNT(*) FROM questions").fetchone()[0] == 10
        assert db.execute("SELECT COUNT(*) FROM answer_options").fetchone()[0] == 30
        assert "admin" not in db.execute("SELECT password_hash FROM advisor_users").fetchone()[0]
        other_firm = db.execute("INSERT INTO firms (name) VALUES (?)", ("Unrelated Firm",)).lastrowid
    assert get_advisor_client(2, other_firm) is None
    try:
        record_decision(2, admin["id"], other_firm, "accepted")
    except PermissionError:
        pass
    else:
        raise AssertionError("Cross-firm advisor decision was accepted")

    app = AppTest.from_file("app.py").run()
    assert not app.exception
    assert any("Better decisions" in item.value for item in app.get("html"))
    app.switch_page("pages/advisor.py").run()
    assert [field.label for field in app.text_input] == ["Username", "Password"]
    assert not any(button.label == "OWNER PORTAL" for button in app.button)
    app.text_input[0].set_value("admin")
    app.text_input[1].set_value("admin")
    app.button(key="FormSubmitter:login_advisor-SIGN IN →").click().run()
    assert not app.exception
    assert [title.value for title in app.title] == ["Client qualification"]
    app.text_input[0].set_value("healthcare").run()
    assert [button.key for button in app.button if button.key.startswith("open_")] == ["open_2"]
    app.button(key="open_2").click().run()
    assert not app.exception
    assert [title.value for title in app.title] == ["Harborlight Health Services"]
    assert [metric.label for metric in app.metric][:4] == [
        "ANNUAL REVENUE", "ANNUAL EBITDA", "EMPLOYEES", "EBITDA MARGIN"
    ]
    assert [metric.value for metric in app.metric][:4] == ["$7.2M", "$1.1M", "42", "14.6%"]
    assert any("DRIVER BREAKDOWN" in item.value for item in app.get("html"))
    assert any('class="score-track"' in item.value and 'width:60%' in item.value for item in app.get("html"))
    assert any(tab.label == "MIXED (8)" for tab in app.tabs)
    app.button(key="action_clarification").click().run()
    assert get_advisor_client(2, admin["firm_id"])["latest_decision"]["decision"] == "clarification"

    # An advisor session cannot open an owner's private result.
    app.switch_page("pages/business.py").run()
    assert [title.value for title in app.title] == []
    assert [field.label for field in app.text_input][:2] == ["Email address", "Password"]
    assert not any(button.label == "ADVISOR SIGN IN" for button in app.button)

    app.text_input(key="signup_owner").set_value("Sam Rivera")
    app.text_input(key="signup_email").set_value("sam@example.com")
    app.text_input(key="signup_business").set_value("Rivera Precision Works")
    app.selectbox(key="signup_industry").set_value("Manufacturing")
    app.number_input(key="signup_revenue").set_value(5_000_000)
    app.number_input(key="signup_ebitda").set_value(800_000)
    app.number_input(key="signup_employees").set_value(32)
    app.text_input(key="signup_password").set_value("ClassroomPass123!")
    app.text_input(key="signup_confirm").set_value("ClassroomPass123!")
    app.button(key="FormSubmitter:business_signup-CREATE ACCOUNT").click().run()
    assert not app.exception
    assert [title.value for title in app.title] == ["Tell us about your business"]
    owner = authenticate_business("sam@example.com", "ClassroomPass123!")
    assert owner is not None
    assert get_business_client(owner["id"])["score"] is None
    profile = get_business_client(owner["id"])
    assert (profile["annual_revenue"], profile["ebitda"], profile["employee_count"]) == (5_000_000, 800_000, 32)
    new_client_id = owner["client_id"]
    try:
        create_business_account(
            owner_name="Different Person", email="SAM@example.com", password="SomePassword123",
            business_name="Duplicate", industry="Other", annual_revenue=1, ebitda=0, employee_count=1,
        )
    except ValueError:
        pass
    else:
        raise AssertionError("Duplicate owner email was accepted")

    for index in range(10):
        assert not app.exception
        assert len(app.radio) == 1
        app.radio[0].set_value("high").run()
        label = "SUBMIT ASSESSMENT →" if index == 9 else "NEXT QUESTION →"
        next_button = next(button for button in app.button if button.label == label)
        next_button.click().run()
    assert not app.exception
    assert [title.value for title in app.title] == ["Rivera Precision Works"]
    assert get_business_client(owner["id"])["score"] == 100
    assert get_advisor_client(new_client_id, admin["firm_id"])["submitted"]
    assert get_advisor_client(new_client_id, admin["firm_id"])["ebitda"] == 800_000
    assert not any('class="readiness-number' in item.value for item in app.get("html"))
    with connection() as db:
        assert db.execute(
            "SELECT COUNT(*) FROM questionnaire_responses WHERE client_id = ?", (new_client_id,)
        ).fetchone()[0] == 10
        assert db.execute(
            "SELECT decision FROM advisor_decisions WHERE client_id = 2 ORDER BY id DESC LIMIT 1"
        ).fetchone()[0] == "clarification"

# Existing databases gain the new columns and preserve seeded fixture details.
with tempfile.TemporaryDirectory() as temp_dir:
    legacy_path = Path(temp_dir) / "legacy.sqlite3"
    with connection(legacy_path) as legacy:
        legacy.execute(
            "CREATE TABLE clients (id INTEGER PRIMARY KEY AUTOINCREMENT, firm_id INTEGER NOT NULL, "
            "business_name TEXT NOT NULL, industry TEXT NOT NULL, annual_revenue INTEGER NOT NULL, "
            "created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)"
        )
        legacy.execute(
            "INSERT INTO clients (firm_id, business_name, industry, annual_revenue) "
            "VALUES (1, 'Legacy Shop', 'Other', 2000000)"
        )
    init_db(legacy_path)
    with connection(legacy_path) as migrated:
        assert migrated.execute("PRAGMA user_version").fetchone()[0] == 2
        columns = {row["name"] for row in migrated.execute("PRAGMA table_info(clients)")}
        assert {"ebitda", "employee_count"} <= columns
        assert tuple(migrated.execute(
            "SELECT ebitda, employee_count FROM clients WHERE business_name = ?",
            ("Northstar Industrial Components",),
        ).fetchone()) == (3_100_000, 95)
        assert tuple(migrated.execute(
            "SELECT ebitda, employee_count FROM clients WHERE business_name = ?",
            ("Legacy Shop",),
        ).fetchone()) == (None, None)

# Simultaneous Streamlit sessions must not race while adding old-schema columns.
from concurrent.futures import ThreadPoolExecutor

with tempfile.TemporaryDirectory() as temp_dir:
    concurrent_path = Path(temp_dir) / "concurrent.sqlite3"
    with connection(concurrent_path) as legacy:
        legacy.execute(
            "CREATE TABLE clients (id INTEGER PRIMARY KEY AUTOINCREMENT, firm_id INTEGER NOT NULL, "
            "business_name TEXT NOT NULL, industry TEXT NOT NULL, annual_revenue INTEGER NOT NULL, "
            "created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)"
        )
    with ThreadPoolExecutor(max_workers=3) as pool:
        list(pool.map(init_db, [concurrent_path] * 3))
    with connection(concurrent_path) as db:
        assert db.execute("SELECT COUNT(*) FROM clients").fetchone()[0] == 3

print("Vetted smoke test passed: routes, admin, signup, wizard, access, persistence, migration, concurrency")
