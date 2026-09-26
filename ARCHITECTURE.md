# Vetted architecture

This document describes the implementation in this repository. Vetted is a Streamlit classroom demo for screening a small or medium business before an M&A sale conversation. It has a public company page, a business-owner assessment, and an advisor review desk. The assessment is a directional screening aid, not a valuation, a verified due-diligence report, or a probability of closing a sale.

## System at a glance

~~~mermaid
flowchart LR
    Browser["Browser: /, /advisor, /business"] --> Router["app.py: Streamlit page router"]
    Router --> Pages["pages/*.py"]
    Pages --> UI["ui.py: views and interactions"]
    UI --> Scoring["scoring.py: points and bands"]
    UI --> Store["database.py: SQL queries and access checks"]
    Store --> Scoring
    Store --> Seed["data.py: question bank and demo clients"]
    Store --> Schema["schema.sql"]
    Store --> SQLite[("SQLite: instance/vetted.sqlite3")]
    UI --> Style["styles.css and assets/vetted-mark.svg"]
~~~

The application is one Python process. Streamlit reruns the relevant page script after user interactions. There is no separate REST API, background worker, message queue, or external database. SQL access is centralized in database.py; the interface does not write directly to SQLite.

| File | Responsibility |
| --- | --- |
| [app.py](app.py) | Sets Streamlit page configuration, initializes SQLite, and registers the three URL routes. |
| [pages/](pages) | Small route entrypoints that call the matching rendering function. |
| [ui.py](ui.py) | Home page, login/signup, owner wizard and result, advisor pipeline and client audit, session state, and actions. |
| [scoring.py](scoring.py) | The ten required answer keys, point values, readiness thresholds, and inverse advisor risk band. |
| [data.py](data.py) | The ten question prompts and answer choices, plus three fictional seed clients. The questions were transcribed from the supplied workbook. |
| [database.py](database.py) | Connection and transaction handling, schema initialization, seed data, authentication, ownership checks, questionnaire storage, client reads, and decision history. |
| [schema.sql](schema.sql) | Eight SQL tables, constraints, foreign keys, and indexes. |
| [styles.css](styles.css), [assets/vetted-mark.svg](assets/vetted-mark.svg) | Bloomberg-inspired dark visual system and brand mark. |
| [smoke_test.py](smoke_test.py) | Isolated end-to-end checks using a temporary SQLite database. |

## Routes and access

| URL | Audience | Behavior |
| --- | --- | --- |
| / | Everyone | Company landing page and links to each portal. |
| /advisor | Advisor | Login when signed out; otherwise pipeline, search/filter/sort, client audit, and decision history. |
| /business | Business owner | Login or signup when signed out; otherwise the ten-question wizard or a read-only result. |

The route registry uses Streamlit's st.navigation with the navigation menu hidden. Role-specific headers do not offer a cross-role dashboard switch. The Vetted brand links to the home page.

The UI records auth_role and auth_user in Streamlit session state. Each protected rendering function checks auth_role before showing its workspace. A successful login stores only the user fields needed by the UI, not the password hash. Sign-out clears authentication, selected client, and unfinished wizard state. Navigation to another role does not grant access to that role.

Backend access checks matter as well: advisor list and detail queries are constrained by firm_id; decision reads and writes verify firm membership; an owner record is found from the signed-in business user ID. The UI currently creates all new business accounts under the first seeded advisor firm.

## Data model

~~~mermaid
erDiagram
    firms ||--o{ advisor_users : employs
    firms ||--o{ clients : owns
    clients ||--o{ business_users : has
    clients ||--o{ questionnaire_responses : submits
    clients ||--o{ advisor_decisions : receives
    questions ||--o{ answer_options : offers
    questions ||--o{ questionnaire_responses : answered_by
    answer_options ||--o{ questionnaire_responses : selected_in
    advisor_users ||--o{ advisor_decisions : records
~~~

| Table | What it stores | Important constraints |
| --- | --- | --- |
| firms | Advisor firms. | Unique name. One firm is seeded today. |
| advisor_users | Advisor username, firm, display name, email, password hash. | Unique username and case-insensitive unique email. |
| clients | Business name, industry, annual revenue, annual EBITDA, employee count, owning firm. | Revenue and employee count must be nonnegative. EBITDA may be negative. |
| business_users | Owner login and the linked client. | Case-insensitive unique email. The current signup creates one client per new owner. |
| questions | Stable field key, prompt, display order. | Unique key and order from 1 to 10. |
| answer_options | High, medium, and low text and points for each question. | Rating and points constrained; unique question/rating pair. |
| questionnaire_responses | Chosen option for each client/question and submission time. | One answer per client/question; composite foreign key keeps the option tied to its question. |
| advisor_decisions | Advisor's accept, reject, or clarification decision, note, and time. | Allowed decision values constrained. Multiple rows retain history. |

SQLite foreign keys are enabled for each connection. Connection handling commits successful operations, rolls back exceptions, and closes the connection. Queries that use user input use SQL parameters. Indexes cover client lookup by firm, responses by client, and recent decisions by client.

The schema permits multiple business_users rows for one client, although the present signup creates a fresh client for every new account. It also permits fewer or more than ten response rows at the database level; the application requires exactly ten before calculating a score or allowing an advisor decision.

On startup, init_db creates the directory and tables if needed. If there is no firm, it seeds one advisor firm, one advisor account, ten questions with three options each, and three fictional clients. Versioned user_version migrations update credentials from an earlier demo and add EBITDA and employee count to existing client tables. The three fictional clients are backfilled with sample profile details. Older owner-created rows keep NULL for fields they never supplied; the advisor view labels them Not provided rather than implying zero. Startup takes a SQLite BEGIN IMMEDIATE write lock before inspecting and migrating columns, so simultaneous Streamlit sessions cannot add the same column twice. Repeated startup calls do not duplicate the seed records.

The default local database path is instance/vetted.sqlite3. VETTED_DB_PATH can override it, which the smoke test uses to isolate its temporary database.

## Readiness and risk calculation engine

### Inputs

calculate_deal_score(answers_dict) in [scoring.py](scoring.py) accepts a mapping from each of these ten field keys to one rating: high, medium, or low.

| # | Field key | Signal being assessed |
| --- | --- | --- |
| 1 | team_execution | Whether employees can operate and decide without the owner. |
| 2 | owner_sales_reliance | Whether sales depend on the owner or a self-sufficient sales team. |
| 3 | relationship_ownership | Whether the team or owner holds customer relationships. |
| 4 | financial_quality | Quality of financial statements, from internal preparation to CPA review. |
| 5 | revenue_growth | Growing, flat/variable, or declining revenue trend. |
| 6 | customer_concentration | Share of revenue from the top **three** customers: under 15%, 15–30%, or over 30%. |
| 7 | key_person_risk | How many departures would materially hurt the business. |
| 8 | legal_cleanliness | Liens, lawsuits, taxes, ownership disputes, and handshake deals. |
| 9 | asset_ownership | Whether critical IP, brand, licenses, and other assets belong to the company. |
| 10 | process_transferability | Whether documented processes could transfer to a new owner. |

The workbook-derived answer text lives in data.py. Each option has a qualitative rating that the owner selects in the wizard. The engine accepts exactly the ten listed keys; missing keys, extra keys, or unknown ratings raise ValueError. A draft or partial questionnaire has no score.

### Formula and bands

Each question has equal weight. High contributes 10 points, medium 5, and low 0:

~~~text
readiness_score = sum(points[rating] for each of the 10 answers)
points = {high: 10, medium: 5, low: 0}
maximum = 10 questions × 10 points = 100
minimum = 0
~~~

Possible scores are 0, 5, 10, ... 100. The score is displayed as a percentage to advisors because the maximum is 100 points; it is a normalized checklist score, not a measured sale probability. Annual revenue, EBITDA, employee count, and computed EBITDA margin are descriptive business profile fields; none contributes points to the scoring function.

| Readiness score | Owner-facing readiness | Advisor-facing risk |
| --- | --- | --- |
| 70–100 | High | Low |
| 40–69 | Medium | Medium |
| 0–39 | Low | High |

score_band computes the readiness label. risk_band reverses that label for the advisor. There is no separate numerical risk model or probability estimate. A high readiness score therefore produces a low risk label. The owner sees only the High/Medium/Low result; the advisor sees the percentage and risk label.

For example, eight high answers and two medium answers yield 8 × 10 + 2 × 5 = **90/100**, or High readiness and Low risk. The seeded client examples are Northstar at 90/Low risk, Harborlight at 60/Medium risk, and Cedar Ridge at 15/High risk.

### When a score is calculated

1. On submission, submit_business_questionnaire calls calculate_deal_score before writing anything. This validates the complete answer set.
2. In one SQLite transaction, it resolves each field key and rating to an answer_options row and inserts ten questionnaire_responses rows. A second submission for the same client is rejected.
3. When a client is read, _client_record loads the stored answer ratings. If it finds ten responses, it calls calculate_deal_score again and adds score and submitted to the returned Python dictionary. The numeric score is **not** stored in clients or a separate score table.
4. The owner and advisor views derive their respective bands from that returned score.

The SQL answer_options.points column records the seeded points, but the active calculator uses the POINTS constant in scoring.py. If someone changes option points in SQL without changing scoring.py, the displayed score will not follow the SQL value. Likewise, changing scoring.py later recalculates existing assessments under the new rule. A versioned scoring policy and stored calculation snapshot would be needed for reproducible historical scores.

### Interpretation

This is a simple, explainable intake rubric. It does not verify answers, weight factors by industry, use financial forecasts, estimate valuation, predict transaction success, or automatically decide whether to represent a client. Advisors make and record that decision separately.

## User and decision flows

### Business owner

1. On /business, the owner first enters business name, industry, annual revenue, annual EBITDA, and employee count, then owner name, email, and password in the signup form.
2. Signup validates required fields, email shape, unique email, nonnegative revenue and employee count, integer EBITDA, and a password of at least eight characters. A negative EBITDA is allowed. It inserts a new client and linked business user in one transaction.
3. The wizard reads questions and answer text from SQL. Current step and draft ratings live in Streamlit session state; they are not durable until submission.
4. The owner submits all ten responses once. The result page then shows a readiness band and a separate read-only answer list. It may show a clarification notice if that is the latest advisor decision.

### Advisor

1. On /advisor, the advisor signs in and sees clients for their firm.
2. The pipeline shows client count, submitted assessment count, average readiness of submitted clients, and count of clients with at least one decision. Search covers company and industry; stage and sort controls refine the list.
3. Selecting a client opens business profile metrics (revenue, EBITDA, employees, and EBITDA margin), workflow, score/risk, signal mix, a grouped driver breakdown, response audit, and decision history. The breakdown separates all ten answers into Strong (10 points), Mixed (5 points), and Needs Attention (0 points) tabs, with each prompt, selected answer, and point contribution visible.
4. An advisor can append an accepted, rejected, or clarification decision with an optional note up to 1,000 characters, but only after all ten answers exist. The latest decision determines the pipeline stage; previous decisions remain in history.

The workflow bar is derived rather than persisted as separate events. A new profile starts at Profile created; ten responses advance it to Score calculated; any decision advances it to Advisor decision. The second step, Form submitted, is marked complete at the same time as the score because submission and scoring happen together. There is no email delivery, form-sent event, or advisor notification service.

## Authentication and security boundary

Passwords are salted with 16 random bytes and hashed with PBKDF2-HMAC-SHA256 using 260,000 iterations. Verification uses a constant-time digest comparison. The seeded advisor login is admin/admin for the classroom build. Seeded owner accounts receive random, undisclosed passwords; new owners choose their own.

This is a demo security model: there is no email verification, password reset, login rate limit, advisor account management screen, or external identity provider. A public deployment with a known advisor password allows anyone to view and change demo records. Use fictional data only. Real client data requires a private deployment, stronger advisor authentication, operational controls, and a durable database.

## Runtime and deployment

- Local: [run_vetted.bat](run_vetted.bat) creates a virtual environment as needed and starts Streamlit bound to 127.0.0.1:8501. SQLite persists on the presenting computer under instance/.
- Cloud: Streamlit Community Cloud runs app.py from the GitHub repository. The classroom demo is at [vetted.streamlit.app](https://vetted.streamlit.app/). The theme comes from .streamlit/config.toml.
- Storage: Cloud SQLite is a local file in the app container. Streamlit Community Cloud does not guarantee persistence of local files, so owner signups, submissions, and decisions may disappear after a restart or redeploy. The three fictional records are seeded again if the database is recreated.
- Scale: Each database call opens its own SQLite connection with a ten-second lock timeout. This is adequate for a small demo, but it is not a multi-instance or durable production data layer. There is no backup or migration framework beyond the small versioned SQLite migrations.

## Verification and change points

Run the local test with the command in [README.md](README.md). [smoke_test.py](smoke_test.py) uses a temporary database and exercises initial seeding, scoring outcomes for fixtures, login, owner signup with all business profile fields, questionnaire submission, advisor metrics and driver grouping, advisor decisions, role boundaries, persistence, and migration from a legacy client table, and concurrent startup against an old schema within that local test. It does not prove cloud storage durability or heavy concurrent usage.

For changes to the rubric, update the question bank in data.py, the required keys/points/thresholds in scoring.py, and the database seed or migration path together. For historical auditability, store a scoring version and score snapshot at submission. For real deployments, move data to a managed database, secure advisor accounts, and add operational monitoring and backups.
