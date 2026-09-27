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
    UI --> Style["styles.css and assets/vetted-mark.png"]
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
| [styles.css](styles.css), [assets/vetted-mark.png](assets/vetted-mark.png) | Bloomberg-inspired dark visual system and header mark. The editable vector source is [assets/vetted-mark.svg](assets/vetted-mark.svg). |
| [smoke_test.py](smoke_test.py) | Isolated end-to-end checks using a temporary SQLite database. |

## Routes and access

| URL | Audience | Behavior |
| --- | --- | --- |
| / | Everyone | Company landing page and links to each portal. |
| /advisor | Advisor | Login when signed out; otherwise pipeline, search/filter/sort, client audit, and decision history. |
| /business | Business owner | Login or signup when signed out; otherwise the ten-question wizard or a read-only result. |

The route registry uses Streamlit's st.navigation with the navigation menu hidden. Role-specific headers do not offer a cross-role dashboard switch. The Vetted mark and wordmark share one home link.

The UI records auth_role and auth_user in Streamlit session state. Each protected rendering function checks auth_role before showing its workspace. A successful login stores only the user fields needed by the UI, not the password hash. Sign-out clears authentication, selected client, and unfinished wizard state. Navigation to another role does not grant access to that role.

Backend access checks matter as well: advisor list and detail queries are constrained by firm_id; decision reads and writes verify firm membership; an owner record is found from the signed-in business user ID. The UI currently creates all new business accounts under the first seeded advisor firm.

## Interface design

The interface keeps a terminal-like visual language but uses clear labels and spacing for a classroom audience. [styles.css](styles.css) defines the shared presentation layer; [ui.py](ui.py) renders the pages. The header mark is the raster [assets/vetted-mark.png](assets/vetted-mark.png), embedded as an image in the home link, with [assets/vetted-mark.svg](assets/vetted-mark.svg) retained as its vector source.

| Visual token | Value | Use |
| --- | --- | --- |
| Background | #08080A | Main canvas. |
| Amber | #FFB100 | Actions, current step, selected tab, and key labels. |
| Cyan | #00F0FF | Profile figures, identifiers, and secondary data. |
| Green | #00FF66 | Strong signals and completed steps. |
| Red | #F04B55; deep red #9B1C2A | Low-rated drivers, high-risk states, and rejected decisions. |

The homepage uses a product preview, direct calls to the two role-specific routes, four capability cards, and a three-step explanation. Advisor pipeline rows have stage-specific badges. The owner wizard displays ten segments so progress corresponds to the ten required responses. Owner result panels change accent with the readiness band. The advisor detail groups company profile metrics, a connected qualification timeline, a score/risk summary, signal counts, and interactive driver tabs. The timeline is horizontal on wide screens and vertical on narrow screens.

The advisor score rail uses the numeric score as its fill width. A 15-point score therefore fills 15% of the rail. Color conveys the readiness/risk band but the score and risk label remain visible as text. Driver cards always show the submitted answer and its point contribution.

"Manage app" at the lower-right of the deployed page is Streamlit Community Cloud's management control for a signed-in workspace member, outside Vetted's page markup. It provides access to Cloud logs and settings; Vetted does not render or configure it. See [Streamlit's app management documentation](https://docs.streamlit.io/deploy/streamlit-community-cloud/manage-your-app).

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
| clients | Business name, industry, annual revenue, annual EBITDA, employee count, owning firm. Money is stored as integer US dollars. | Revenue and employee count must be nonnegative. EBITDA may be negative. EBITDA and employee count can be NULL for legacy records that never supplied them. |
| business_users | Owner login and the linked client. | Case-insensitive unique email. The current signup creates one client per new owner. |
| questions | Stable field key, prompt, display order. | Unique key and order from 1 to 10. |
| answer_options | High, medium, and low text and points for each question. | Rating and points constrained; unique question/rating pair. |
| questionnaire_responses | Chosen option for each client/question and submission time. | One answer per client/question; composite foreign key keeps the option tied to its question. |
| advisor_decisions | Advisor's accept, reject, or clarification decision, note, and time. | Allowed decision values constrained. Multiple rows retain history. |

SQLite foreign keys are enabled for each connection. Connection handling commits successful operations, rolls back exceptions, and closes the connection. Queries that use user input use SQL parameters. Indexes cover client lookup by firm, responses by client, and recent decisions by client.

The schema permits multiple business_users rows for one client, although the present signup creates a fresh client for every new account. The database can hold an incomplete response set; the application requires exactly ten responses before calculating a score or allowing an advisor decision. The unique question order, constrained to 1 through 10, limits the seeded question bank to ten questions.

On startup, init_db creates the directory and tables if needed. If there is no firm, it seeds one advisor firm, one advisor account, ten questions with three options each, and three fictional clients. Versioned user_version migrations update credentials from an earlier demo and add EBITDA and employee count to existing client tables. The three fictional clients are backfilled with sample profile details. Older owner-created rows keep NULL for fields they never supplied; the advisor view labels them Not provided rather than implying zero. Startup takes a SQLite BEGIN IMMEDIATE write lock before inspecting and migrating columns, so simultaneous Streamlit sessions cannot add the same column twice. Repeated startup calls do not duplicate the seed records.

The default local database path is instance/vetted.sqlite3. VETTED_DB_PATH can override it, which the smoke test uses to isolate its temporary database.

## Data movement

1. The owner submits business profile fields and account credentials. create_business_account inserts one clients row and one linked business_users row in a single transaction.
2. The owner wizard loads questions and their three answer choices from SQL. Draft ratings exist only in Streamlit session state until the owner submits all ten.
3. submit_business_questionnaire validates the complete rating map with calculate_deal_score, then inserts one questionnaire_responses row per question in a transaction. The foreign key ensures each selected option belongs to its question.
4. On each client read, database.py joins responses to questions and options, derives the readiness score, and returns the client profile, score, answers, and most recent advisor decision to ui.py.
5. An advisor decision appends an advisor_decisions row. The pipeline stage uses the latest decision while the full history remains available.

Profile dollars and employee count are stored separately from answers. No revenue, EBITDA, employee-count, or margin value enters the ten-question calculation.

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

Each question has equal weight. Let H, M, and L be the counts of high, medium, and low responses. A complete assessment has H + M + L = 10:

~~~text
readiness_score = 10 x H + 5 x M + 0 x L
minimum = 0; maximum = 100
advisor_risk = inverse(readiness_band(readiness_score))
~~~

The calculation uses the qualitative rating attached to each selected answer. It does not parse the answer text or infer additional points from financial profile fields.

Possible scores are 0, 5, 10, ... 100. The score is displayed as a percentage to advisors because the maximum is 100 points; it is a normalized checklist score, not a measured sale probability. Annual revenue, EBITDA, employee count, and computed EBITDA margin are descriptive business profile fields; none contributes points to the scoring function.

| Readiness score | Owner-facing readiness | Advisor-facing risk |
| --- | --- | --- |
| 70–100 | High | Low |
| 40–69 | Medium | Medium |
| 0–39 | Low | High |

score_band computes the readiness label. risk_band reverses that label for the advisor. There is no separate numerical risk model or probability estimate. A high readiness score therefore produces a low risk label. The owner sees only the High/Medium/Low result; the advisor sees the percentage and risk label.

For example, eight high answers and two medium answers yield 8 × 10 + 2 × 5 = **90/100**, or High readiness and Low risk. The seeded client examples are Northstar at 90/Low risk, Harborlight at 60/Medium risk, and Cedar Ridge at 15/High risk.

### Business profile and driver interpretation

The advisor profile shows annual revenue, annual EBITDA, number of employees, and EBITDA margin. Margin is calculated for display as EBITDA / annual revenue x 100. If revenue is zero or EBITDA is unknown, the margin is N/A. The UI rounds money to one decimal place in millions; SQLite retains the entered whole-dollar values.

The advisor overview sorts the ten submitted responses into Strong (high, 10 points), Mixed (medium, 5 points), and Needs Attention (low, 0 points). Each tab shows every matching driver with its question, selected answer, and score contribution. These groups explain the total; they are not separate weighted models. The signal-mix counts sum to ten for a submitted questionnaire.

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

The connected timeline is derived rather than persisted as separate events. Immediately after signup, Business profile is complete and Questionnaire is current. After the ten answers are submitted, Business profile, Questionnaire, and Readiness score are complete, while Advisor decision is current. Once an advisor records a decision, all four steps are complete. Submission and scoring occur together, so there is no separately timed calculation event. There is no email delivery, form-sent event, or advisor notification service.

## Authentication and security boundary

Passwords are salted with 16 random bytes and hashed with PBKDF2-HMAC-SHA256 using 260,000 iterations. Verification uses a constant-time digest comparison. The seeded advisor login is admin/admin for the classroom build. Seeded owner accounts receive random, undisclosed passwords; new owners choose their own.

This is a demo security model: there is no email verification, password reset, login rate limit, advisor account management screen, or external identity provider. A public deployment with a known advisor password allows anyone to view and change demo records. Use fictional data only. Real client data requires a private deployment, stronger advisor authentication, operational controls, and a durable database.

## Runtime and deployment

- Local: [run_vetted.bat](run_vetted.bat) creates a virtual environment as needed and starts Streamlit bound to 127.0.0.1:8501. SQLite persists on the presenting computer under instance/.
- Cloud: Streamlit Community Cloud runs app.py from the GitHub repository. The classroom demo is at [vetted.streamlit.app](https://vetted.streamlit.app/). The theme comes from .streamlit/config.toml.
- Storage: Cloud SQLite is a local file in the app container. Streamlit Community Cloud does not guarantee persistence of local files, so owner signups, submissions, and decisions may disappear after a restart or redeploy. The three fictional records are seeded again if the database is recreated.
- Scale: Each database call opens its own SQLite connection with a ten-second lock timeout. This is adequate for a small demo, but it is not a multi-instance or durable production data layer. There is no backup or migration framework beyond the small versioned SQLite migrations.

## Verification and change points

Run the local test with the command in [README.md](README.md). [smoke_test.py](smoke_test.py) uses temporary databases and exercises initial seeding, fixture scores, login, owner signup with business profile fields, questionnaire submission, the advisor timeline and driver grouping, advisor decisions, role boundaries, persistence, legacy-schema migration, and concurrent startup. It does not prove cloud storage durability or heavy concurrent usage.

For changes to the rubric, update the question bank in data.py, the required keys/points/thresholds in scoring.py, and the database seed or migration path together. For historical auditability, store a scoring version and score snapshot at submission. For real deployments, move data to a managed database, secure advisor accounts, and add operational monitoring and backups.
