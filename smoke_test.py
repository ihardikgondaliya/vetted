"""Check routes, signup, questionnaire submission, and SQLite persistence."""

import os
import tempfile
from pathlib import Path

from streamlit.testing.v1 import AppTest


with tempfile.TemporaryDirectory() as temp_dir:
    os.environ["VETTED_DB_PATH"] = str(Path(temp_dir) / "vetted-test.sqlite3")

    from ui import stage_for
    from database import (  # imported after setting the isolated database path
        authenticate_advisor,
        authenticate_business,
        business_decision_history,
        connection,
        create_business_account,
        get_advisor_client,
        get_business_client,
        init_db,
        list_advisor_clients,
        record_decision,
        respond_to_clarification,
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
    assert any('class="score-track caution"' in item.value and 'width:60%' in item.value for item in app.get("html"))
    assert any('class="timeline-panel"' in item.value and '03 / 04 COMPLETE' in item.value
               and 'timeline-step current' in item.value for item in app.get("html"))
    assert any(tab.label == "MIXED (8)" for tab in app.tabs)
    next(field for field in app.text_area if field.label == "Message to business owner").set_value("Please provide the missing contract details.").run()
    next(field for field in app.text_area if field.label == "Internal advisor note").set_value("Internal diligence note.").run()
    app.button(key="action_clarification").click().run()
    assert get_advisor_client(2, admin["firm_id"])["latest_decision"]["decision"] == "clarification"
    assert any("04 / 04 COMPLETE" in item.value for item in app.get("html"))

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
    assert any('class="question-progress"' in item.value and 'aria-valuenow="1"' in item.value
               for item in app.get("html"))
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
    assert any("AWAITING ADVISOR REVIEW" in item.value for item in app.get("html"))

    # Exercise the live two-session path: advisor update, owner refresh, owner
    # clarification reply, then both final decision outcomes.
    advisor_app = AppTest.from_file("app.py").run()
    advisor_app.switch_page("pages/advisor.py").run()
    advisor_app.text_input[0].set_value("admin")
    advisor_app.text_input[1].set_value("admin")
    next(button for button in advisor_app.button if button.label.startswith("SIGN IN")).click().run()
    advisor_app.button(key=f"open_{new_client_id}").click().run()
    assert not advisor_app.exception
    advisor_app.button(key="action_clarification").click().run()
    assert get_advisor_client(new_client_id, admin["firm_id"])["latest_decision"] is None
    assert any("Enter a message telling the owner" in str(item.value) for item in advisor_app.error)

    next(field for field in advisor_app.text_area if field.label == "Message to business owner").set_value("Please identify the customer contracts that renew next year.").run()
    next(field for field in advisor_app.text_area if field.label == "Internal advisor note").set_value("Internal valuation concern: check contract terms.").run()
    advisor_app.button(key="action_clarification").click().run()
    latest = get_advisor_client(new_client_id, admin["firm_id"])["latest_decision"]
    assert latest["decision"] == "clarification"
    assert latest["owner_message"] == "Please identify the customer contracts that renew next year."
    assert "note" not in get_business_client(owner["id"])["latest_decision"]
    app.button(key="owner_refresh").click().run()
    assert not app.exception
    assert any("CLARIFICATION REQUESTED" in item.value for item in app.get("html"))
    assert any("Please identify the customer contracts" in item.value for item in app.get("html"))
    assert all("Internal valuation concern" not in str(item.value) for item in app.get("html"))
    assert all("note" not in update for update in business_decision_history(owner["id"]))
    unrelated_owner = create_business_account(
        owner_name="Taylor Lee", email="taylor@example.com", password="ClassroomPass123!",
        business_name="Separate Workshop", industry="Manufacturing",
        annual_revenue=1_000_000, ebitda=100_000, employee_count=8,
    )
    assert business_decision_history(unrelated_owner["id"]) == []
    try:
        respond_to_clarification(unrelated_owner["id"], "A response for someone else's request")
    except ValueError:
        pass
    else:
        raise AssertionError("Unrelated owner replied to another client's clarification")

    reply = "The three renewals are scheduled for March, June, and October."
    next(field for field in app.text_area if field.label == "Reply to the advisor").set_value(reply).run()
    next(button for button in app.button if button.label == "SEND CLARIFICATION").click().run()
    assert not app.exception
    assert get_business_client(owner["id"])["latest_decision"]["reply_message"] == reply
    assert any("CLARIFICATION SENT" in item.value for item in app.get("html"))
    try:
        respond_to_clarification(owner["id"], "A duplicate reply")
    except ValueError:
        pass
    else:
        raise AssertionError("Duplicate clarification reply was accepted")
    advisor_app.run()
    assert any("Owner clarification received" in str(item.value) for item in advisor_app.info)
    assert any(reply in str(item.value) for item in advisor_app.markdown)
    assert stage_for(get_advisor_client(new_client_id, admin["firm_id"])) == "Clarification received"

    next(field for field in advisor_app.text_area if field.label == "Message to business owner").set_value("We would like to discuss representing your business.").run()
    advisor_app.button(key="action_accepted").click().run()
    app.button(key="owner_refresh").click().run()
    assert any("REPRESENTATION ACCEPTED" in item.value for item in app.get("html"))
    assert any("We would like to discuss representing" in item.value for item in app.get("html"))
    assert stage_for(get_advisor_client(new_client_id, admin["firm_id"])) == "Accepted"

    next(field for field in advisor_app.text_area if field.label == "Message to business owner").set_value("After further review, we cannot take this engagement.").run()
    advisor_app.button(key="action_rejected").click().run()
    app.button(key="owner_refresh").click().run()
    assert any("NOT MOVING FORWARD" in item.value for item in app.get("html"))
    assert any("After further review" in item.value for item in app.get("html"))
    assert stage_for(get_advisor_client(new_client_id, admin["firm_id"])) == "Rejected"
    assert len(business_decision_history(owner["id"])) == 3
    returning_owner = AppTest.from_file("app.py").run()
    returning_owner.switch_page("pages/business.py").run()
    next(field for field in returning_owner.text_input if field.label == "Email address").set_value("sam@example.com")
    next(field for field in returning_owner.text_input if field.label == "Password").set_value("ClassroomPass123!")
    next(button for button in returning_owner.button if button.label.startswith("SIGN IN")).click().run()
    assert not returning_owner.exception
    assert any("NOT MOVING FORWARD" in item.value for item in returning_owner.get("html"))
    try:
        respond_to_clarification(owner["id"], "Too late")
    except ValueError:
        pass
    else:
        raise AssertionError("Reply after final decision was accepted")
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
        legacy.execute(
            "CREATE TABLE advisor_decisions (id INTEGER PRIMARY KEY, client_id INTEGER NOT NULL "
            "REFERENCES clients(id), advisor_user_id INTEGER NOT NULL REFERENCES advisor_users(id), "
            "decision TEXT NOT NULL, note TEXT NOT NULL DEFAULT '', "
            "decided_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)"
        )
    init_db(legacy_path)
    with connection(legacy_path) as migrated:
        assert migrated.execute("PRAGMA user_version").fetchone()[0] == 3
        columns = {row["name"] for row in migrated.execute("PRAGMA table_info(clients)")}
        assert {"ebitda", "employee_count"} <= columns
        decision_columns = {row["name"] for row in migrated.execute("PRAGMA table_info(advisor_decisions)")}
        assert "owner_message" in decision_columns
        assert migrated.execute(
            "SELECT owner_message FROM advisor_decisions LIMIT 1"
        ).fetchone()[0] == ""
        assert migrated.execute("SELECT name FROM sqlite_master WHERE name = 'clarification_replies'").fetchone()
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

print("Vetted smoke test passed: routes, signup, wizard, all decisions, owner updates, replies, access, migration, concurrency")
