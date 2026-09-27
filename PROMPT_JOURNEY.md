# Building Vetted with Codex

*A concise, presentation-ready reconstruction of the prompts behind [Vetted](https://vetted.streamlit.app/). These are polished summaries of the project direction, not a transcript.*

## 1. Define the product

> Act as a senior Python developer. Build **Vetted**, a Streamlit application that helps small-business owners assess sale readiness and helps M&A advisors qualify opportunities. Create separate owner and advisor experiences. Use the supplied ten-question workbook as the source for the assessment, include three fictional clients for a working demo, and keep the scoring transparent and explainable.

## 2. Build the data and decision workflow

> Make the application fully runnable. Store users, business profiles, answers, and advisor decisions in SQL tables. Let owners create accounts, enter company details, complete the questionnaire, and see an overall High, Medium, or Low readiness result. Give advisors a searchable client pipeline, the numeric score, a breakdown of strong and weak drivers, and actions to accept, reject, or request clarification. Show advisor updates in the owner portal and allow owners to reply to clarification requests.

## 3. Design the experience

> Create a polished, responsive interface inspired by financial terminals: near-black surfaces, amber accents, cyan data, green positive signals, red concerns, and monospaced typography. Make the homepage explain the problem Vetted solves and guide visitors to the right portal. Use clear cards, a workflow timeline, and interactive details instead of dense text. Keep each role focused on its own tasks and make the VETTED logo return to the homepage.

## 4. Verify and ship

> Give the app separate `/`, `/advisor`, and `/business` URLs. Provide local run instructions, automated checks for scoring and the full advisor-to-owner decision loop, and an architecture document explaining the database, access rules, and calculation engine. Publish the code to GitHub, deploy the classroom demo, and verify navigation and the main workflows on the live site. Document any demo limitations clearly.

## What the class can learn

The project grew through **specific, testable refinements**: first the product and users, then persistent data and business logic, then complete cross-role workflows, and finally visual polish and live verification. The result is a working prototype rather than a collection of disconnected screens.

See [ARCHITECTURE.md](ARCHITECTURE.md) for the implementation and [README.md](README.md) for the demo walkthrough. The public build uses demo authentication and non-durable Cloud storage; use fictional business information.