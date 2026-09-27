# Vetted: Development Prompts

## 1. Product foundation

> Build Vetted as a Python Streamlit application for M&A deal readiness. Provide separate business-owner and advisor portals, a public homepage, ten qualification questions based on the supplied workbook, and three realistic sample clients.

## 2. Data, scoring, and workflow

> Use SQL tables for accounts, company profiles, questionnaire responses, and advisor decisions. Let owners sign up, submit company details and answers, and view a High, Medium, or Low readiness result. Calculate a transparent 0–100 score from the ten responses. Give advisors a searchable pipeline, numeric score, risk band, driver breakdown, and accept, reject, or clarification actions. Show decisions and clarification replies in the owner portal.

## 3. Interface design

> Design a responsive, financial-terminal-inspired interface with a clear information hierarchy, dark surfaces, amber actions, and color-coded results. Explain the product's purpose on the homepage. Present advisor progress as a timeline, make client analysis interactive, and keep each portal focused on its user's tasks.

## 4. Delivery and verification

> Make the app runnable locally and deploy it with `/`, `/advisor`, and `/business` routes. Document the architecture and scoring logic. Test signup, scoring, access controls, all advisor decisions, and owner updates. Verify the deployed navigation and workflows.