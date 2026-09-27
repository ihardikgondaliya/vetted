# How I built Vetted with Codex: a prompt journey

This is a classroom summary of the requests that shaped [Vetted](https://vetted.streamlit.app/), an M&A sale-readiness demo. The prompts below are **condensed paraphrases in the order they were given**, not a verbatim export of the conversation. Account credentials and other private details from deployment requests have been omitted.

## The starting idea

The first prompt asked Codex, acting as a Python developer, to build a dark, Bloomberg-inspired Streamlit app for two audiences: M&A advisors and business owners. The working title was **DealQuant**; the finished product is **Vetted**. The initial requirements already included ten qualification questions, a 0–100 score, three fictional clients, a searchable advisor table, a client audit and decision workflow, and a simpler owner result view.

The app's core problem became clearer in later prompts: a company's revenue alone does not show whether its people, customer relationships, records, assets, and processes will hold up during a sale. Owners need a readable starting point; advisors need a consistent intake record and a way to explain their next decision.

## The prompts, in sequence

| Stage | Condensed prompt I gave Codex | What it added or changed |
| --- | --- | --- |
| 1. Product concept | “Build a clean, dark-themed Streamlit M&A qualification app with advisor and business-owner views, ten scored questions, mock clients, and accept/reject/clarification actions.” | The initial two-sided workflow, scoring function, seed data, and terminal-inspired visual direction. |
| 2. Real routes and data | “Give advisors `/advisor` and owners `/business`. Store data in SQL tables, add login schemas and pages, and make the app runnable for a live classroom demo.” | Separate URL routes, SQLite schema and queries, authentication, setup instructions, and a local launcher. |
| 3. Product-facing home | “Research and design a company homepage. Remove the role-switch buttons inside each portal, make both workspaces more interactive, and support business-owner signup.” | A public landing page, cleaner role boundaries, owner accounts, and a less text-heavy interface. |
| 4. Hosting plan | “Can this be hosted for free for about 48 hours?” | A Streamlit Community Cloud deployment path and an explanation of its demo-sized hosting tradeoffs. |
| 5. Brand navigation | “Clicking the VETTED logo or name should take me home.” | A shared, clickable brand lockup. A later live check revealed that embedded Cloud navigation needed a native Streamlit page link. |
| 6. GitHub and deployment | “Upload the app to my GitHub repository and host it. The accounts are connected; deploy it.” | The code was pushed to GitHub and deployed as a public Streamlit app. Private credentials supplied during setup are intentionally excluded from this handout. |
| 7. Architecture | “Write an architecture file explaining the application, SQL model, workflow, and overall risk calculation engine.” | `ARCHITECTURE.md`, with component relationships, data flow, scoring formula, access checks, and deployment limits. |
| 8. Better intake and advisor analysis | “Have owners enter business name, industry, revenue, EBITDA, and employee count first. In each advisor client profile, show those facts and a breakdown of strong, mixed, and attention-needed drivers. Shorten the live URL.” | Structured company profiles, a driver audit alongside the overall score, and the `vetted.streamlit.app` address. |
| 9. Visual polish | “Review the whole app like a staff engineer and designer. Make the home and workspaces more professional, turn the advisor workflow into a timeline, and refine the terminal colors.” | Responsive page layouts, a connected workflow display, stronger visual hierarchy, and consistent semantic colors. The Cloud “Manage app” control was identified as Streamlit's UI, not an app element. |
| 10. Complete the decision loop | “Verify acceptance, rejection, and clarification. How does the owner learn what the advisor decided? Add an owner workflow or update view if needed, and update the architecture.” | An in-app owner status dashboard, owner-visible advisor messages, clarification replies, decision history, and tests covering all three outcomes. |
| 11. Flagship pass | “Explain the problem Vetted solves in more detail, make the homepage eye-catching, and make the VETTED brand return to the root URL from `/advisor`.” | A problem-led homepage, illustrative qualification screen, five-stage process, interactive role previews, and a native home link verified on the deployed site. |

Screenshots and the supplied **Vetting App for M&A firms - questions and answers.xlsx** workbook gave Codex concrete reference material. The workbook supplied the ten question and answer choices; the screenshots exposed layout, navigation, and branding problems that text requirements alone did not show.

## How the app fits together

- `app.py` and `pages/` register the public, advisor, and owner routes.
- `ui.py`, `styles.css`, and `assets/` render the workflow and visual design.
- `data.py` holds the question bank and fictional sample clients.
- `scoring.py` calculates readiness: **High = 10 points, Medium = 5, Low = 0** for each of ten answers. The total is 0–100. Owners see a High/Medium/Low readiness band; advisors see the numeric percentage, inverse risk band, and individual drivers. This is a screening index, not a probability of sale.
- `schema.sql` and `database.py` define and access SQLite tables for users, companies, questions, answers, advisor decisions, and owner clarification replies.
- `smoke_test.py` checks signup, scoring, routes, access boundaries, all advisor decisions, owner updates, replies, and migrations.

For the full technical explanation, see [ARCHITECTURE.md](ARCHITECTURE.md). For local run and demo instructions, see [README.md](README.md).

## What this demonstrates about prompting

1. **Start with a concrete user and workflow.** The first prompt named both audiences, their screens, the ten inputs, and the decisions the app had to support.
2. **Add real operating constraints early.** URLs, SQL storage, login, a runnable launcher, and live demo requirements turned a mockup into a working application.
3. **Use actual source material.** The workbook anchored the question set; screenshots made visual and navigation defects specific.
4. **Ask for end-to-end behavior, not just screens.** “How does the owner get updates?” led to persisted advisor messages, an owner status view, and clarification replies.
5. **Test deployed behavior.** A logo link that worked locally did not update the outer Cloud URL. The final prompt called out the exact wrong and desired URLs, making the fix verifiable.
6. **Ask for documentation and verification.** Architecture notes and smoke tests make the result explainable to teammates and easier to change.

## A reusable prompt pattern

```text
Act as a [role]. Build [product] for [users] who need to [goal].
Use [technology and design constraints].
The required workflow is [steps and decisions].
Persist [data] and calculate [rules] transparently.
Use [attached source material] as the source of truth.
Make it runnable with [commands/deployment target].
Test [critical user journeys], explain limitations, and update the docs.
```

Vetted remains a **classroom demo**. Its public demo advisor login and local SQLite file on Streamlit Community Cloud are not suitable for real client records. Use fictional data when presenting it.