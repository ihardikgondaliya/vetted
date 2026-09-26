"""Vetted presentation and role-specific user flows."""

from __future__ import annotations

from collections import Counter
from html import escape
from pathlib import Path

import streamlit as st

from database import (
    authenticate_advisor,
    authenticate_business,
    create_business_account,
    decision_history,
    get_advisor_client,
    get_business_client,
    list_advisor_clients,
    questionnaire_questions,
    record_decision,
    submit_business_questionnaire,
)
from scoring import POINTS, risk_band, score_band


APP_DIR = Path(__file__).resolve().parent
DRIVER_TITLES = {
    "team_execution": "Team independence",
    "owner_sales_reliance": "Sales independence",
    "relationship_ownership": "Customer relationships",
    "financial_quality": "Financial reporting",
    "revenue_growth": "Revenue trajectory",
    "customer_concentration": "Customer concentration",
    "key_person_risk": "Key people",
    "legal_cleanliness": "Legal position",
    "asset_ownership": "Asset ownership",
    "process_transferability": "Process transferability",
}
def html(markup: str) -> None:
    st.html(markup)


def format_money(amount: int, decimals: int = 1) -> str:
    sign = "-" if amount < 0 else ""
    return f"{sign}${abs(amount) / 1_000_000:,.{decimals}f}M"


def format_revenue(amount: int) -> str:
    return format_money(amount)


def stage_for(client: dict) -> str:
    if not client["submitted"]:
        return "Questionnaire open"
    decision = client["latest_decision"]
    return {
        None: "Awaiting decision",
        "accepted": "Accepted",
        "rejected": "Rejected",
        "clarification": "Clarification requested",
    }[decision["decision"] if decision else None]


def band_class(band: str) -> str:
    return {"High": "positive", "Medium": "caution", "Low": "negative"}[band]


def clear_auth() -> None:
    for key in ("auth_role", "auth_user", "selected_client_id", "draft_answers", "question_step"):
        st.session_state.pop(key, None)


def render_header(role: str = "home") -> None:
    st.html(APP_DIR / "styles.css")
    brand, controls = st.columns([3.7, 1.8], vertical_alignment="center")
    with brand:
        mark_svg = (APP_DIR / "assets" / "vetted-mark.svg").read_text(encoding="utf-8")
        html(
            '<a class="brand-lockup" href="/" aria-label="Vetted home">'
            f'{mark_svg}<span class="brand-copy">'
            '<span class="brand-name">VETTED<span>.</span></span>'
            '<span class="brand-caption">DEAL READINESS, MADE CLEAR</span>'
            '</span></a>'
        )
    with controls:
        if role == "home":
            advisor, owner = st.columns(2)
            if advisor.button("ADVISOR SIGN IN", key="home_nav_advisor", use_container_width=True):
                st.switch_page("pages/advisor.py")
            if owner.button("OWNER PORTAL", key="home_nav_owner", use_container_width=True):
                st.switch_page("pages/business.py")
        elif st.session_state.get("auth_role") == role:
            badge, signout = st.columns([1.2, 1])
            badge.markdown(f'<div class="role-badge">{role.upper()} WORKSPACE</div>', unsafe_allow_html=True)
            if signout.button("SIGN OUT", key=f"signout_{role}", use_container_width=True):
                clear_auth()
                st.rerun()
        else:
            if st.button("← BACK TO VETTED", key=f"back_home_{role}", use_container_width=True):
                st.switch_page("pages/home.py")
    html('<div class="header-rule"></div>')


def section_label(text: str, number: str | None = None) -> None:
    lead = f'<span class="section-number">{escape(number)}</span>' if number else ""
    html(f'<div class="section-label">{lead}{escape(text)}</div>')


def render_home() -> None:
    render_header("home")
    hero_text, hero_visual = st.columns([1.12, 0.88], gap="large", vertical_alignment="center")
    with hero_text:
        html(
            '<div class="eyebrow">A STRUCTURED START TO THE SALE CONVERSATION</div>'
            '<div class="hero-title">Better decisions<br>begin&nbsp;<em>before</em> the deal.</div>'
            '<p class="hero-copy">Vetted helps business owners understand sale readiness and gives '
            'M&A advisors a consistent way to qualify opportunities. One focused assessment, '
            'two views, and a clearer next step.</p>'
        )
        start, advisor = st.columns([1.15, 1])
        if start.button("ASSESS YOUR BUSINESS →", type="primary", use_container_width=True):
            st.switch_page("pages/business.py")
        if advisor.button("ADVISOR ACCESS", use_container_width=True):
            st.switch_page("pages/advisor.py")
        html('<div class="hero-foot">10 VETTING SIGNALS <span>·</span> 3 READINESS BANDS <span>·</span> 1 SHARED RECORD</div>')
    with hero_visual:
        html(
            '<div class="terminal"><div class="terminal-head"><span>V / READINESS ENGINE</span>'
            '<span class="live-dot"></span></div>'
            '<div class="terminal-overline">ILLUSTRATIVE ASSESSMENT</div>'
            '<div class="terminal-title">A clearer operating picture.</div>'
            '<div class="signal-row"><span>OWNER DEPENDENCE</span><div class="signal-track"><i style="width:78%"></i></div><b>01</b></div>'
            '<div class="signal-row"><span>FINANCIAL CLARITY</span><div class="signal-track"><i style="width:62%"></i></div><b>02</b></div>'
            '<div class="signal-row"><span>CUSTOMER MIX</span><div class="signal-track"><i style="width:44%"></i></div><b>03</b></div>'
            '<div class="signal-row"><span>TRANSFERABILITY</span><div class="signal-track"><i style="width:70%"></i></div><b>04</b></div>'
            '<div class="terminal-bottom"><span>IDENTIFY THE SIGNALS</span><span>→</span><span>DECIDE THE NEXT STEP</span></div></div>'
        )

    html('<div class="home-divider"></div>')
    section_label("WHAT VETTED DOES", "01")
    html(
        '<div class="section-intro">A practical first look at the business behind the numbers.</div>'
        '<p class="section-copy">Selling a business involves more than a headline revenue figure. '
        'Vetted brings operating, financial, customer, legal, and transfer questions into '
        'one structured intake, so both sides can start with the same facts.</p>'
    )
    features = (
        ("01", "Operating independence", "Understand whether the team can deliver and decide without the owner."),
        ("02", "Financial visibility", "Surface the quality of statements and the direction of revenue."),
        ("03", "Concentration and risk", "See exposure to key customers, people, and unresolved legal issues."),
        ("04", "Transferability", "Check whether assets and documented processes can move with the business."),
    )
    feature_cols = st.columns(4, gap="small")
    for column, (number, title, description) in zip(feature_cols, features):
        with column:
            html(
                f'<div class="feature-card"><span>{number} / SIGNAL</span><h3>{escape(title)}</h3>'
                f'<p>{escape(description)}</p></div>'
            )

    html('<div class="home-divider"></div>')
    section_label("HOW THE PLATFORM WORKS", "02")
    steps = (
        ("01", "Create your business profile", "Owners open a private account and enter basic company information."),
        ("02", "Answer ten focused questions", "A guided assessment captures the choices from the supplied vetting framework."),
        ("03", "Review and decide", "Owners see a simple readiness band; advisors see the full audit and record a decision."),
    )
    step_cols = st.columns(3, gap="medium")
    for column, (number, title, description) in zip(step_cols, steps):
        with column:
            html(
                f'<div class="process-card"><div class="process-index">{number}</div>'
                f'<h3>{escape(title)}</h3><p>{escape(description)}</p></div>'
            )

    html('<div class="home-divider"></div>')
    section_label("BUILT FOR BOTH SIDES", "03")
    left, right = st.columns(2, gap="large")
    with left:
        html(
            '<div class="audience-card owner"><span>FOR BUSINESS OWNERS</span><h3>Clarity without the deal jargon.</h3>'
            '<p>Complete the assessment at your pace, see an overall High, Medium, or Low '
            'readiness result, and keep a copy of your submitted answers.</p></div>'
        )
    with right:
        html(
            '<div class="audience-card advisor"><span>FOR M&A ADVISORS</span><h3>A repeatable qualification desk.</h3>'
            '<p>Search the pipeline, review each answer, compare readiness percentages, '
            'and record accept, reject, or clarification decisions.</p></div>'
        )

    with st.expander("What does the readiness result mean?"):
        st.write(
            "The result summarizes answers to ten qualification questions. It is a directional "
            "screening tool, not a business valuation, transaction probability, or guarantee of a sale."
        )
    with st.expander("Why assess a business before a sale process?"):
        st.write(
            "Planning an ownership transfer includes understanding the business's value, assets, "
            "liabilities, and preparation needs. Vetted organizes a focused first-pass discussion."
        )
        st.link_button(
            "Read SBA guidance on selling a business",
            "https://www.sba.gov/counseling/manage-your-business/",
        )
    html(
        '<div class="home-footer"><div><strong>Start with the facts.</strong><span>Get a clearer view of what comes next.</span></div></div>'
    )
    if st.button("CREATE A BUSINESS ACCOUNT →", key="home_final_cta", type="primary"):
        st.switch_page("pages/business.py")


def render_login(role: str) -> None:
    render_header(role)
    owner = role == "business"
    copy, panel = st.columns([0.95, 1.05], gap="large")
    with copy:
        html(
            '<div class="eyebrow">'
            + ("OWNER PORTAL / PRIVATE ACCESS" if owner else "ADVISOR DESK / RESTRICTED ACCESS")
            + '</div><div class="login-title">'
            + ("Make your next move<br><em>with clarity.</em>" if owner else "Welcome back,<br><em>advisor.</em>")
            + '</div><p class="login-copy">'
            + (
                "Create an account to complete the ten-question assessment, or sign in to review your result."
                if owner else "Sign in to review the client pipeline, questionnaire signals, and representation decisions."
            )
            + "</p>"
        )
        html(
            '<div class="login-points"><div>01 <span>PRIVATE, ROLE-SCOPED ACCESS</span></div>'
            '<div>02 <span>STRUCTURED TEN-QUESTION INTAKE</span></div>'
            '<div>03 <span>PERSISTENT DECISION RECORD</span></div></div>'
        )
    with panel:
        if owner:
            signin, signup = st.tabs(["SIGN IN", "CREATE ACCOUNT"])
            with signin:
                _login_form("business")
            with signup:
                _signup_form()
        else:
            section_label("ADVISOR SIGN IN")
            _login_form("advisor")


def _login_form(role: str) -> None:
    with st.form(f"login_{role}", border=True):
        identity = st.text_input("Email address" if role == "business" else "Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("SIGN IN →", type="primary", use_container_width=True)
    if submitted:
        authenticate = authenticate_business if role == "business" else authenticate_advisor
        user = authenticate(identity, password)
        if not user:
            st.error("The account details do not match. Please try again.")
            return
        clear_auth()
        st.session_state.auth_role = role
        st.session_state.auth_user = user
        st.switch_page("pages/business.py" if role == "business" else "pages/advisor.py")


def _signup_form() -> None:
    with st.form("business_signup", border=True):
        st.markdown("#### 01 / BUSINESS PROFILE")
        business_name = st.text_input("Business name", key="signup_business")
        industry = st.selectbox(
            "Industry",
            ("Select an industry", "Manufacturing", "Healthcare", "Professional Services", "Food & Beverage", "Technology", "Retail", "Other"),
            key="signup_industry",
        )
        revenue_col, ebitda_col = st.columns(2)
        annual_revenue = revenue_col.number_input(
            "Annual revenue (USD)", min_value=0, max_value=1_000_000_000,
            value=None, step=100_000, key="signup_revenue",
        )
        ebitda = ebitda_col.number_input(
            "Annual EBITDA (USD)", min_value=-1_000_000_000, max_value=1_000_000_000,
            value=None, step=50_000, key="signup_ebitda",
            help="Earnings before interest, taxes, depreciation, and amortization. A negative value is allowed.",
        )
        employee_count = st.number_input(
            "Number of employees", min_value=0, max_value=100_000,
            value=None, step=1, key="signup_employees",
        )
        st.markdown("#### 02 / OWNER ACCOUNT")
        owner_name = st.text_input("Your name", key="signup_owner")
        email = st.text_input("Work email", key="signup_email")
        password = st.text_input("Create password", type="password", key="signup_password")
        confirm = st.text_input("Confirm password", type="password", key="signup_confirm")
        submitted = st.form_submit_button("CREATE ACCOUNT", type="primary", use_container_width=True)
    if submitted:
        if industry == "Select an industry":
            st.error("Choose an industry.")
        elif annual_revenue is None or ebitda is None or employee_count is None:
            st.error("Enter annual revenue, annual EBITDA, and number of employees.")
        elif password != confirm:
            st.error("Passwords do not match.")
        else:
            try:
                user = create_business_account(
                    owner_name=owner_name,
                    email=email,
                    password=password,
                    business_name=business_name,
                    industry=industry,
                    annual_revenue=annual_revenue,
                    ebitda=ebitda,
                    employee_count=employee_count,
                )
            except ValueError as exc:
                st.error(str(exc))
            else:
                clear_auth()
                st.session_state.auth_role = "business"
                st.session_state.auth_user = user
                st.switch_page("pages/business.py")


def render_workflow(client: dict) -> None:
    position = 4 if client["latest_decision"] else 3 if client["submitted"] else 1
    labels = ("Profile created", "Form submitted", "Score calculated", "Advisor decision")
    markup = []
    for index, label in enumerate(labels, start=1):
        state = "done" if index < position or (index == 4 and client["latest_decision"]) else "active" if index == position else "pending"
        markup.append(
            f'<div class="flow-step {state}"><b>0{index}</b><span>{escape(label)}</span></div>'
        )
    html('<div class="flow-track">' + "".join(markup) + "</div>")


def render_advisor_list(user: dict) -> None:
    clients = list_advisor_clients(user["firm_id"])
    html('<div class="eyebrow">ADVISOR DESK / PIPELINE</div>')
    st.title("Client qualification")
    st.caption("Search submitted opportunities, review risk signals, and record the next decision.")

    submitted = [client for client in clients if client["submitted"]]
    decisions = sum(client["latest_decision"] is not None for client in clients)
    average = round(sum(client["score"] for client in submitted) / len(submitted)) if submitted else 0
    metrics = st.columns(4)
    for column, label, value, note in zip(
        metrics,
        ("CLIENTS", "ASSESSMENTS", "AVERAGE READINESS", "DECISIONS"),
        (len(clients), len(submitted), f"{average}%" if submitted else "—", decisions),
        ("In pipeline", "Submitted", "Submitted clients", "Recorded"),
    ):
        with column:
            st.metric(label, value, help=note)

    section_label("PIPELINE EXPLORER", "01")
    search_col, stage_col, sort_col = st.columns([2.2, 1.2, 1.2])
    search = search_col.text_input("Search", placeholder="Company or industry", key="advisor_search").strip().casefold()
    stage_filter = stage_col.selectbox(
        "Stage", ("All stages", "Questionnaire open", "Awaiting decision", "Accepted", "Rejected", "Clarification requested"),
    )
    sort = sort_col.selectbox("Sort", ("Company A–Z", "Highest score", "Lowest score", "Newest first"))
    rows = [
        client for client in clients
        if (not search or search in f'{client["business_name"]} {client["industry"]}'.casefold())
        and (stage_filter == "All stages" or stage_for(client) == stage_filter)
    ]
    if sort == "Highest score":
        rows.sort(key=lambda c: c["score"] if c["score"] is not None else -1, reverse=True)
    elif sort == "Lowest score":
        rows.sort(key=lambda c: c["score"] if c["score"] is not None else 101)
    elif sort == "Newest first":
        rows.sort(key=lambda c: c["id"], reverse=True)
    st.caption(f"{len(rows)} of {len(clients)} client records")
    if not rows:
        st.info("No clients match these filters.")
        return
    for client in rows:
        stage = stage_for(client)
        score_text = f'{client["score"]}%' if client["score"] is not None else "PENDING"
        risk_text = f'{risk_band(client["score"])} RISK' if client["score"] is not None else "AWAITING ANSWERS"
        color = band_class(score_band(client["score"])) if client["score"] is not None else "neutral"
        with st.container(border=True):
            main, industry, status, score, action = st.columns(
                [2.8, 1.6, 1.8, 1.1, 1], vertical_alignment="center"
            )
            main.markdown(f"**{escape(client['business_name'])}**")
            main.caption(format_revenue(client["annual_revenue"]) + " annual revenue")
            industry.caption(client["industry"])
            status.markdown(f'<span class="status-pill">{escape(stage)}</span>', unsafe_allow_html=True)
            score.markdown(
                f'<div class="row-score {color}">{score_text}</div><div class="row-risk">{risk_text}</div>',
                unsafe_allow_html=True,
            )
            if action.button("OPEN →", key=f'open_{client["id"]}', use_container_width=True):
                st.session_state.selected_client_id = client["id"]
                st.rerun()


def render_advisor_detail(user: dict, client_id: int) -> None:
    client = get_advisor_client(client_id, user["firm_id"])
    if client is None:
        st.error("Client not found in your firm.")
        return
    if st.button("← BACK TO PIPELINE", key="back_pipeline"):
        st.session_state.pop("selected_client_id", None)
        st.rerun()
    html('<div class="eyebrow">CLIENT AUDIT / ' + escape(stage_for(client)).upper() + '</div>')
    st.title(client["business_name"])
    st.caption(client["industry"])
    section_label("BUSINESS PROFILE")
    revenue = client["annual_revenue"]
    ebitda = client["ebitda"]
    margin = f"{ebitda / revenue * 100:,.1f}%" if revenue and ebitda is not None else "N/A"
    for column, label, value in zip(
        st.columns(4),
        ("ANNUAL REVENUE", "ANNUAL EBITDA", "EMPLOYEES", "EBITDA MARGIN"),
        (format_money(revenue), format_money(ebitda) if ebitda is not None else "Not provided",
         f'{client["employee_count"]:,}' if client["employee_count"] is not None else "Not provided", margin),
    ):
        column.metric(label, value)
    render_workflow(client)
    if not client["submitted"]:
        st.info("This business has created an account and has not submitted its questionnaire yet.")
        return

    overview, answers, decision_tab = st.tabs(["OVERVIEW", "QUESTIONNAIRE", "DECISION & HISTORY"])
    with overview:
        score = client["score"]
        risk = risk_band(score)
        color = {"Low": "positive", "Medium": "caution", "High": "negative"}[risk]
        left, right = st.columns([1.05, 0.95], gap="large")
        with left:
            html(
                f'<div class="readiness-card"><div class="card-label">DEAL READINESS</div>'
                f'<div class="readiness-number {color}">{score}<small>%</small></div>'
                f'<div class="risk-label {color}">{risk.upper()} RISK</div>'
                '<p>Higher readiness indicates fewer concerns across the ten vetting signals.</p></div>'
            )
            st.progress(score / 100, text="Overall readiness")
        with right:
            counts = Counter(response["rating"] for response in client["responses"])
            section_label("SIGNAL MIX")
            for rating, label, color_name in (
                ("high", "Strong", "positive"),
                ("medium", "Mixed", "caution"),
                ("low", "Needs attention", "negative"),
            ):
                count = counts[rating]
                html(
                    f'<div class="mix-row"><span class="{color_name}">{label}</span>'
                    f'<div class="mix-track"><i class="{color_name}" style="width:{count * 10}%"></i></div>'
                    f'<b>{count:02d}</b></div>'
                )
        section_label("DRIVER BREAKDOWN")
        st.caption(
            "Each answer contributes 0, 5, or 10 points to the readiness score. "
            "The business profile above provides context and does not change the score."
        )
        attention_tab, mixed_tab, strong_tab = st.tabs(
            [
                f"NEEDS ATTENTION ({counts['low']})",
                f"MIXED ({counts['medium']})",
                f"STRONG ({counts['high']})",
            ]
        )
        for tab, rating, empty in (
            (attention_tab, "low", "No drivers need attention."),
            (mixed_tab, "medium", "No mixed drivers."),
            (strong_tab, "high", "No strong drivers."),
        ):
            with tab:
                drivers = [item for item in client["responses"] if item["rating"] == rating]
                if not drivers:
                    st.info(empty)
                for item in drivers:
                    title = DRIVER_TITLES.get(item["field_key"], item["field_key"].replace("_", " ").title())
                    css_class = {"low": "attention", "medium": "mixed", "high": "strong"}[rating]
                    html(
                        f'<div class="driver-card {css_class}">'
                        f'<div class="driver-head"><h4>{escape(title)}</h4>'
                        f'<span>{POINTS[rating]} / 10 POINTS</span></div>'
                        f'<p>{escape(item["prompt"])}</p>'
                        f'<div class="driver-answer">{escape(item["answer_text"])}</div>'
                        '</div>'
                    )
    with answers:
        section_label("QUESTIONNAIRE AUDIT")
        rating_filter = st.selectbox("Show responses", ("All", "High", "Medium", "Low"))
        filtered = [
            answer for answer in client["responses"]
            if rating_filter == "All" or answer["rating"] == rating_filter.lower()
        ]
        st.caption(f"{len(filtered)} of 10 responses")
        for answer in filtered:
            with st.expander(f'{answer["display_order"]:02d}  /  {answer["prompt"]}'):
                st.markdown(f"**Submitted answer:** {answer['answer_text']}")
                st.caption(f"Signal: {answer['rating'].title()}")
    with decision_tab:
        section_label("RECORD A DECISION")
        st.caption("Each decision is added to the audit history. The most recent decision appears in the pipeline.")
        notice = st.session_state.pop("decision_notice", None)
        if notice:
            st.success(notice)
        note = st.text_area("Decision note", placeholder="Context or clarification request (optional)", max_chars=1000)
        accept, reject, clarify = st.columns(3)
        for column, label, decision, kind in (
            (accept, "ACCEPT REPRESENTATION", "accepted", "primary"),
            (reject, "REJECT DEAL", "rejected", "secondary"),
            (clarify, "REQUEST CLARIFICATION", "clarification", "secondary"),
        ):
            if column.button(label, key=f"action_{decision}", type=kind, use_container_width=True):
                record_decision(client_id, user["id"], user["firm_id"], decision, note)
                st.session_state.decision_notice = "Decision saved to the audit history."
                st.rerun()
        section_label("DECISION HISTORY")
        history = decision_history(client_id, user["firm_id"])
        if not history:
            st.info("No decisions have been recorded for this client.")
        for item in history:
            with st.container(border=True):
                st.markdown(f"**{item['decision'].replace('_', ' ').title()}**  ·  {item['decided_at']} UTC")
                st.caption(f"Recorded by {item['advisor_name']}")
                if item["note"]:
                    st.write(item["note"])


def render_advisor() -> None:
    if st.session_state.get("auth_role") != "advisor":
        render_login("advisor")
        return
    render_header("advisor")
    user = st.session_state.auth_user
    client_id = st.session_state.get("selected_client_id")
    if client_id:
        render_advisor_detail(user, client_id)
    else:
        render_advisor_list(user)


def render_owner_wizard(user: dict, client: dict) -> None:
    questions = questionnaire_questions()
    draft = st.session_state.setdefault("draft_answers", {})
    step = st.session_state.setdefault("question_step", 0)
    step = max(0, min(step, len(questions) - 1))
    question = questions[step]
    html('<div class="eyebrow">BUSINESS OWNER / READINESS ASSESSMENT</div>')
    st.title("Tell us about your business")
    st.caption(f'{client["business_name"]}  ·  Answer ten focused questions to see your readiness result.')
    st.progress((step + 1) / len(questions), text=f"Question {step + 1} of {len(questions)}")
    html(f'<div class="question-index">SIGNAL {step + 1:02d} / 10</div>')
    st.subheader(question["prompt"])
    choices = question["options"]
    current = draft.get(question["field_key"])
    rating = st.radio(
        "Choose the answer that best describes your business",
        ("high", "medium", "low"),
        index=("high", "medium", "low").index(current) if current else None,
        format_func=lambda value: choices[value],
        key=f'answer_{question["field_key"]}',
    )
    if rating:
        draft[question["field_key"]] = rating
    html('<div class="wizard-rule"></div>')
    previous, spacer, next_step = st.columns([1, 1.2, 1.25])
    if previous.button("← PREVIOUS", disabled=step == 0, use_container_width=True):
        st.session_state.question_step = step - 1
        st.rerun()
    if step < len(questions) - 1:
        if next_step.button("NEXT QUESTION →", disabled=rating is None, type="primary", use_container_width=True):
            st.session_state.question_step = step + 1
            st.rerun()
    elif next_step.button("SUBMIT ASSESSMENT →", disabled=rating is None, type="primary", use_container_width=True):
        try:
            submit_business_questionnaire(user["id"], dict(draft))
        except ValueError as exc:
            st.error(str(exc))
        else:
            st.session_state.pop("draft_answers", None)
            st.session_state.pop("question_step", None)
            st.rerun()


def render_owner_result(client: dict) -> None:
    band = score_band(client["score"])
    color = band_class(band)
    messages = {
        "High": "Your answers show strong readiness across the ten vetting signals.",
        "Medium": "Your answers show a mixed profile with some areas to strengthen.",
        "Low": "Several readiness areas may need attention before a sale process.",
    }
    html('<div class="eyebrow">BUSINESS OWNER / PRIVATE RESULT</div>')
    st.title(client["business_name"])
    st.caption("Your submitted assessment, in one clear view.")
    overview, answers = st.tabs(["YOUR RESULT", "YOUR ANSWERS"])
    with overview:
        html(
            f'<div class="owner-result"><div class="card-label">OVERALL SALE READINESS</div>'
            f'<div class="owner-result-band {color}">{band.upper()}</div>'
            f'<p>{escape(messages[band])}</p><div class="result-meta">10 / 10 ANSWERS SUBMITTED</div></div>'
        )
        section_label("WHAT HAPPENS NEXT")
        with st.container(border=True):
            st.markdown("**Your assessment is complete.**")
            st.write(
                "Your answers are available for advisor review. This result is a starting point "
                "for a conversation about preparation, not a valuation or promise of a sale."
            )
        if client["latest_decision"] and client["latest_decision"]["decision"] == "clarification":
            st.info("An advisor has requested clarification. Contact your advisor for the next step.")
    with answers:
        section_label("SUBMITTED QUESTIONNAIRE")
        st.caption("Read-only copy of your ten responses")
        for answer in client["responses"]:
            with st.expander(f'{answer["display_order"]:02d}  /  {answer["prompt"]}'):
                st.write(answer["answer_text"])


def render_business() -> None:
    if st.session_state.get("auth_role") != "business":
        render_login("business")
        return
    render_header("business")
    user = st.session_state.auth_user
    client = get_business_client(user["id"])
    if client is None:
        st.error("Your business record could not be found.")
        return
    if client["submitted"]:
        render_owner_result(client)
    else:
        render_owner_wizard(user, client)
