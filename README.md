# Vetted

See [ARCHITECTURE.md](ARCHITECTURE.md) for the system design, SQL model, user flows, and readiness/risk calculation.

Vetted is a Streamlit M&A readiness application that runs locally and on Streamlit Community Cloud. Business owners create an account, answer ten guided questions, and see an overall High, Medium, or Low readiness result. Advisors review the client pipeline, see percentages and response details, and record decisions. The ten questions and answer choices come from `Vetting App for M&A firms - questions and answers.xlsx`.

## Start the app

On Windows, double-click `run_vetted.bat`. It creates a virtual environment, installs dependencies if needed, and starts Streamlit.

Or run from PowerShell in this folder:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py --server.address 127.0.0.1 --server.port 8501
```

Open these pages on the presenting computer:

| Page | Address |
| --- | --- |
| About Vetted | http://localhost:8501/ |
| Advisor | http://localhost:8501/advisor |
| Business owner | http://localhost:8501/business |

Keep the terminal open while presenting; press `Ctrl+C` to stop. The Windows launcher and PowerShell command bind to the presenting computer only.

## Deploy for a classroom demo

Push the project to GitHub and create an app at [Streamlit Community Cloud](https://share.streamlit.io/) using `app.py` as the entrypoint. Choose Python 3.12 if prompted. The deployed routes are `/`, `/advisor`, and `/business` under the assigned `*.streamlit.app` URL. The cloud host supplies its own network binding; the local launcher keeps using `127.0.0.1`.

The app seeds three fictional clients on first launch. Its SQLite database lives in the app's local filesystem. Streamlit Community Cloud does not guarantee that local files survive a reboot, redeploy, or hibernation, so signups, answers, and decisions can reset during the demo. Use fictional details only. The advisor account is `admin` / `admin` for this classroom build; anyone with the public URL can use it. Restrict the app to invited viewers or change the advisor authentication before collecting real information. After the presentation, delete the cloud app from your Streamlit workspace.

## Classroom walkthrough

1. On `/business`, select **Create account**. Enter a new business and a password with at least eight characters.
2. Answer the ten questions in the guided wizard and submit. The owner view shows only an overall readiness band, with submitted answers in a separate tab.
3. Sign out. On `/advisor`, sign in with username **`admin`** and password **`admin`**.
4. Search for the new business, inspect its score and answer audit, then record an advisor decision.

The advisor pipeline also begins with three sample businesses to make the first demo screen useful. Their old publicly shared owner passwords have been disabled. New business users sign up with their own credentials.

## Data and scoring

SQLite stores data at `instance/vetted.sqlite3`. The first start creates the database and sample records. Data persists across restarts. [schema.sql](schema.sql) defines firms, advisor users, business users, clients, questions, answer options, responses, and advisor decisions. New business accounts and their questionnaires are written to these tables. Passwords are salted and hashed with PBKDF2-SHA256.

Each High answer contributes 10 points, Medium 5, and Low 0. The owner-facing band is High at 70–100, Medium at 40–69, and Low at 0–39. Advisors see the percentage and inverse risk band. The result is a directional screening tool, not a valuation or a probability of sale.

The homepage describes the product and links to the [U.S. Small Business Administration's business management guidance](https://www.sba.gov/counseling/manage-your-business/) for broader sale preparation context.

## Verify

```powershell
.\.venv\Scripts\python.exe smoke_test.py
```

The test creates a temporary database and checks routing, admin login, owner signup, the ten-question flow, advisor decisions, access boundaries, and persistence.
