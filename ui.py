"""Vetted presentation and role-specific user flows."""

from __future__ import annotations

from collections import Counter
import base64
from html import escape
from pathlib import Path

import streamlit as st

from database import (
    authenticate_advisor,
    authenticate_business,
    business_decision_history,
    create_business_account,
    decision_history,
    get_advisor_client,
    get_business_client,
    list_advisor_clients,
    questionnaire_questions,
    record_decision,
    respond_to_clarification,
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
    if decision and decision["decision"] == "clarification" and decision["reply_message"]:
        return "Clarification received"
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
        mark_png = base64.b64encode((APP_DIR / "assets" / "vetted-mark.png").read_bytes()).decode("ascii")
        html(f'<style>:root {{--vetted-mark: url("data:image/png;base64,{mark_png}");}}</style>')
        with st.container(key="brand_home"):
            st.page_link("pages/home.py", label="VETTED.", help="Go to Vetted home")
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
    html(
        '<div class="home-marketline"><span><i></i> VETTED / PRE-DEAL INTELLIGENCE</span>'
        '<span>OWNER ASSESSMENT <b>/</b> ADVISOR REVIEW <b>/</b> DECISION RECORD</span></div>'
    )

    hero_text, hero_visual = st.columns([1.04, 0.96], gap="large", vertical_alignment="center")
    with hero_text:
        html(
            '<div class="home-hero-kicker">A CLEARER START TO THE SALE CONVERSATION</div>'
            '<div class="home-hero-title">Know the business.<br><em>Before the deal.</em></div>'
            '<p class="home-hero-copy">A revenue number cannot tell you who owns customer relationships, '
            'whether the team can operate without the founder, or what a buyer will find in diligence. '
            'Vetted brings the questions that matter into one focused assessment, so owners understand '
            'what needs work and advisors can qualify opportunities with a consistent record.</p>'
        )
        start, advisor = st.columns([1.12, 1], gap="small")
        if start.button("ASSESS YOUR BUSINESS", key="home_hero_owner", type="primary", use_container_width=True):
            st.switch_page("pages/business.py")
        if advisor.button("ENTER ADVISOR DESK", key="home_hero_advisor", use_container_width=True):
            st.switch_page("pages/advisor.py")
        html(
            '<div class="home-hero-proof"><span><b>10</b> STRUCTURED SIGNALS</span>'
            '<span><b>02</b> PURPOSE-BUILT VIEWS</span>'
            '<span><b>01</b> SHARED DECISION RECORD</span></div>'
        )
    with hero_visual:
        html(
            '<div class="home-screen" aria-label="Illustrative Vetted assessment preview">'
            '<div class="home-screen-top"><span><i></i> V / QUALIFICATION SCREEN</span>'
            '<span>ILLUSTRATIVE DATA</span></div>'
            '<div class="home-screen-main"><div class="home-screen-id">SAMPLE BUSINESS / 001</div>'
            '<div class="home-screen-company">Aster Precision Works</div>'
            '<div class="home-screen-industry">MANUFACTURING <span>/</span> PRE-DEAL ASSESSMENT</div>'
            '<div class="home-screen-score"><div><small>READINESS INDEX</small>'
            '<strong>65<em>/100</em></strong></div><div><span class="home-screen-band">MEDIUM READINESS</span>'
            '<p>4 strong / 5 mixed / 1 needs attention</p></div></div>'
            '<div class="home-screen-section">SIGNAL DETAIL <span>CONTRIBUTION</span></div>'
            '<div class="home-screen-row"><span>OWNER INDEPENDENCE</span><i class="positive"></i><b>STRONG</b></div>'
            '<div class="home-screen-row"><span>FINANCIAL QUALITY</span><i class="caution"></i><b>MIXED</b></div>'
            '<div class="home-screen-row"><span>CUSTOMER CONCENTRATION</span><i class="negative"></i><b>ATTENTION</b></div>'
            '<div class="home-screen-row"><span>PROCESS TRANSFERABILITY</span><i class="caution"></i><b>MIXED</b></div>'
            '</div><div class="home-screen-bottom"><span>EXPLAINABLE SIGNALS</span>'
            '<span>OWNER VIEW + ADVISOR VIEW</span></div></div>'
        )

    html('<div class="home-section-rule"></div>')
    html(
        '<div class="home-section-kicker">01 / THE PROBLEM</div>'
        '<div class="home-section-headline">Most sale conversations start with the number.<br>'
        '<em>The real questions arrive later.</em></div>'
        '<p class="home-section-copy">Small-business owners may not know how a buyer will assess the '
        'business beyond revenue. Advisors can receive incomplete or inconsistent intake information. '
        'Questions about customer concentration, key people, financial records, legal exposure, and '
        'transferable assets then surface across separate calls and documents. Vetted puts those '
        'questions in front of both sides at the start.</p>'
    )
    problems = (
        ("01", "BUSINESS OWNER", "Readiness feels opaque", "Know which operating strengths are clear and which areas may need attention before a sale process begins."),
        ("02", "M&A ADVISOR", "Intake is hard to compare", "Review the same ten signals for every opportunity, with the original answers beside the calculated score."),
        ("03", "THE CONVERSATION", "Decisions lack a shared record", "Keep the assessment, advisor decision, owner update, and clarification reply in one traceable workflow."),
    )
    for column, (number, audience, title, copy) in zip(st.columns(3, gap="small"), problems):
        with column:
            html(
                f'<div class="home-problem-card accent-{number}"><div><span>{number} / 03</span><b>{audience}</b></div>'
                f'<h3>{escape(title)}</h3><p>{escape(copy)}</p></div>'
            )

    html('<div class="home-section-rule"></div>')
    html(
        '<div class="home-section-kicker">02 / THE WORKFLOW</div>'
        '<div class="home-section-headline">One intake. A visible path forward.</div>'
        '<p class="home-section-copy">The owner supplies the context. Vetted translates ten '
        'self-reported signals into an explainable readiness band. The advisor reviews the drivers '
        'and records a next step the owner can see.</p>'
    )
    stages = (
        ("01", "Profile", "Company, industry, revenue, EBITDA, and team size."),
        ("02", "Assessment", "Ten focused operating, financial, and transfer questions."),
        ("03", "Readiness", "High, Medium, or Low from a transparent points rubric."),
        ("04", "Advisor review", "Full answer audit, risk view, and driver breakdown."),
        ("05", "Next step", "Accept, reject, or ask the owner for clarification."),
    )
    html(
        '<div class="home-flow">' + ''.join(
            f'<div class="home-flow-step"><span>{number}</span><h3>{escape(title)}</h3>'
            f'<p>{escape(copy)}</p></div>' for number, title, copy in stages
        ) + '</div>'
    )

    html('<div class="home-section-rule"></div>')
    html(
        '<div class="home-section-kicker">03 / TWO PURPOSE-BUILT VIEWS</div>'
        '<div class="home-section-headline">Clarity for the owner. Depth for the advisor.</div>'
        '<p class="home-section-copy">Each person sees the information needed for their decision. '
        'The business owner gets a plain-language result and update history. The advisor gets '
        'the score, the source answers, and a place to record an accountable decision.</p>'
    )
    owner_tab, advisor_tab = st.tabs(["BUSINESS OWNER VIEW", "M&A ADVISOR VIEW"])
    with owner_tab:
        left, right = st.columns([1.1, .9], gap="large", vertical_alignment="center")
        with left:
            html(
                '<div class="home-role-kicker">PRIVATE OWNER WORKSPACE</div>'
                '<div class="home-role-title">Know where you stand.<br>Know what happens next.</div>'
                '<p class="home-role-copy">Create a business profile, answer the ten questions, '
                'and see one overall readiness band. Your dashboard keeps the submitted answers '
                'read-only and shows the latest advisor decision. If more detail is needed, '
                'reply to the clarification request in the same portal.</p>'
                '<div class="home-role-points"><span>01 / SIMPLE READINESS BAND</span>'
                '<span>02 / PRIVATE ANSWER RECORD</span><span>03 / ADVISOR UPDATES</span></div>'
            )
            if st.button("OPEN OWNER PORTAL", key="home_role_owner", type="primary"):
                st.switch_page("pages/business.py")
        with right:
            html(
                '<div class="home-role-preview owner"><div>YOUR READINESS</div>'
                '<strong>MEDIUM</strong><p>Your assessment is complete and ready for advisor review.</p>'
                '<div class="home-role-status"><i></i> AWAITING ADVISOR REVIEW</div>'
                '<small>ILLUSTRATIVE OWNER VIEW</small></div>'
            )
    with advisor_tab:
        left, right = st.columns([1.1, .9], gap="large", vertical_alignment="center")
        with left:
            html(
                '<div class="home-role-kicker">M&A ADVISOR DESK</div>'
                '<div class="home-role-title">See the drivers.<br>Record the judgment.</div>'
                '<p class="home-role-copy">Search a client pipeline, inspect profile metrics '
                'and every submitted answer, and see which signals are strong, mixed, or need '
                'attention. The score is a screening index; the decision remains with the advisor.</p>'
                '<div class="home-role-points"><span>01 / CLIENT PIPELINE</span>'
                '<span>02 / SCORE + DRIVER AUDIT</span><span>03 / DECISION HISTORY</span></div>'
            )
            if st.button("OPEN ADVISOR DESK", key="home_role_advisor", type="primary"):
                st.switch_page("pages/advisor.py")
        with right:
            html(
                '<div class="home-role-preview advisor"><div>QUALIFICATION SNAPSHOT</div>'
                '<strong>65<span>%</span></strong><p>MEDIUM RISK / ILLUSTRATIVE CLIENT</p>'
                '<div class="home-role-bars"><span>STRONG <b style="width:40%"></b> 04</span>'
                '<span>MIXED <b style="width:50%"></b> 05</span>'
                '<span>ATTENTION <b style="width:10%"></b> 01</span></div>'
                '<small>EXPLAINABLE FROM THE TEN RESPONSES</small></div>'
            )

    html('<div class="home-section-rule"></div>')
    html(
        '<div class="home-section-kicker">04 / AN EXPLAINABLE ENGINE</div>'
        '<div class="home-section-headline">A score you can trace back to the answer.</div>'
        '<p class="home-section-copy">Every response contributes the same number of possible '
        'points. The owner sees an overall readiness band; the advisor sees the 0-100 index '
        'and the strong, mixed, and attention drivers behind it. This is a directional screening '
        'tool, not a valuation or a predicted probability of sale.</p>'
        '<div class="home-method"><div><b class="positive">10</b><span>POINTS / STRONG</span></div>'
        '<div><b class="caution">05</b><span>POINTS / MIXED</span></div>'
        '<div><b class="negative">00</b><span>POINTS / NEEDS ATTENTION</span></div>'
        '<div class="home-method-result"><strong>10 SIGNALS</strong><span>SUM TO A 0-100 READINESS INDEX</span></div></div>'
    )
    html(
        '<div class="home-final"><div><span>START WITH A CLEARER PICTURE</span>'
        '<strong>Make the first conversation count.</strong>'
        '<p>Bring the business, the signals, and the next step into one place.</p></div></div>'
    )
    owner_cta, advisor_cta, space = st.columns([1, 1, 1.3], gap="small")
    if owner_cta.button("ASSESS YOUR BUSINESS", key="home_final_owner", type="primary", use_container_width=True):
        st.switch_page("pages/business.py")
    if advisor_cta.button("ADVISOR SIGN IN", key="home_final_advisor", use_container_width=True):
        st.switch_page("pages/advisor.py")
    html('<div class="home-disclaimer">VETTED / M&A READINESS SCREENING / SELF-REPORTED INPUTS / ADVISOR DECISION REQUIRED</div>')



def render_login(role: str) -> None:
    render_header(role)
    owner = role == "business"
    copy, panel = st.columns([0.95, 1.05], gap="large")
    with copy:
        html(
            '<div class="eyebrow">'
            + ("OWNER PORTAL / PRIVATE ACCESS" if owner else "ADVISOR DESK / RESTRICTED ACCESS")
            + '</div><div class="login-title">'
            + ("Make your next move<br><em>with clarity.</em>" if owner else "Your next decision<br><em>starts here.</em>")
            + '</div><p class="login-copy">'
            + (
                "Create your business profile, complete the assessment, and return for advisor updates in one private workspace."
                if owner else "Sign in to review client context, compare readiness drivers, and record the next step with a clear audit trail."
            )
            + "</p>"
        )
        if owner:
            stages = (("01", "BUSINESS PROFILE"), ("02", "TEN SIGNALS"),
                      ("03", "READINESS RESULT"), ("04", "ADVISOR UPDATE"))
        else:
            stages = (("01", "CLIENT PIPELINE"), ("02", "DRIVER AUDIT"),
                      ("03", "DECISION RECORD"), ("04", "OWNER UPDATE"))
        html(
            '<div class="login-map"><div class="login-map-head">'
            '<span>YOUR WORKSPACE</span><b>V / ACCESS</b></div>'
            + ''.join(
                f'<div class="login-map-row"><span>{number}</span><strong>{label}</strong>'
                '<i></i></div>' for number, label in stages
            ) + '</div>'
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
    """Render the derived four-stage qualification timeline."""
    complete_count = 4 if client["latest_decision"] else 3 if client["submitted"] else 1
    steps = (
        ("Business profile", "Company details captured"),
        ("Questionnaire", "Ten owner responses"),
        ("Readiness score", "Ten signals calculated"),
        ("Advisor decision", "Representation outcome"),
    )
    markup = []
    for index, (title, detail) in enumerate(steps, start=1):
        state = "done" if index <= complete_count else "current" if index == complete_count + 1 else "upcoming"
        label = "COMPLETE" if state == "done" else "IN PROGRESS" if state == "current" else "UP NEXT"
        current = ' aria-current="step"' if state == "current" else ""
        markup.append(
            f'<li class="timeline-step {state}"{current}>'
            f'<div class="timeline-node"><span>{index:02d}</span></div>'
            f'<div class="timeline-copy"><span class="timeline-state">{label}</span>'
            f'<strong>{escape(title)}</strong><small>{escape(detail)}</small></div></li>'
        )
    html(
        '<section class="timeline-panel" aria-label="Qualification timeline">'
        '<div class="timeline-heading"><span>QUALIFICATION TIMELINE</span>'
        f'<b>{complete_count:02d} / 04 COMPLETE</b></div>'
        '<ol class="timeline-track">' + "".join(markup) + "</ol></section>"
    )


def render_advisor_list(user: dict) -> None:
    clients = list_advisor_clients(user["firm_id"])
    html('<div class="eyebrow">ADVISOR DESK / PIPELINE</div>')
    st.title("Opportunity desk")
    st.caption("Review the pipeline, inspect each driver, and record a clear next step.")

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

    review_queue = sum(stage_for(client) in {"Awaiting decision", "Clarification received"} for client in clients)
    queue_label = "opportunity" if review_queue == 1 else "opportunities"
    html(
        '<div class="pipeline-brief"><div><span>REVIEW QUEUE</span>'
        f'<strong>{review_queue:02d} {queue_label} need advisor action</strong>'
        '<p>New assessments and answered clarification requests appear here.</p></div>'
        '<div class="pipeline-brief-end">PIPELINE / LIVE RECORDS</div></div>'
    )
    section_label("PIPELINE EXPLORER", "01")
    search_col, stage_col, sort_col = st.columns([2.2, 1.2, 1.2])
    search = search_col.text_input("Search", placeholder="Company or industry", key="advisor_search").strip().casefold()
    stage_filter = stage_col.selectbox(
        "Stage", ("All stages", "Questionnaire open", "Awaiting decision", "Accepted", "Rejected", "Clarification requested", "Clarification received"),
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
        with st.container(border=True, key=f'pipeline_client_{client["id"]}'):
            main, industry, status, score, action = st.columns(
                [2.8, 1.6, 1.8, 1.1, 1], vertical_alignment="center"
            )
            main.markdown(f"**{escape(client['business_name'])}**")
            main.caption(format_revenue(client["annual_revenue"]) + " annual revenue")
            industry.caption(client["industry"])
            stage_tone = {
                "Accepted": "accepted",
                "Rejected": "rejected",
                "Clarification requested": "clarification",
                "Clarification received": "received",
                "Questionnaire open": "open",
            }.get(stage, "awaiting")
            status.markdown(
                f'<span class="status-pill {stage_tone}">{escape(stage)}</span>',
                unsafe_allow_html=True,
            )
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
    html(
        f'<div class="client-meta"><span>{escape(client["industry"])}</span>'
        f'<span>CLIENT {client["id"]:04d}</span><span>{escape(stage_for(client))}</span></div>'
    )
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
                f'<div class="readiness-card {color}"><div class="card-label">DEAL READINESS</div>'
                f'<div class="readiness-number {color}">{score}<small>%</small></div>'
                f'<div class="risk-label {color}">{risk.upper()} RISK</div>'
                '<p>Higher readiness indicates fewer concerns across the ten vetting signals.</p></div>'
            )
            html(
                f'<div class="score-scale"><span>READINESS INDEX</span><b>{score} / 100</b></div>'
                f'<div class="score-track {color}" role="progressbar" aria-label="Overall readiness" '
                f'aria-valuemin="0" aria-valuemax="100" aria-valuenow="{score}">'
                f'<i style="width:{score}%"></i></div>'
            )
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
        if client["latest_decision"] and client["latest_decision"]["reply_message"]:
            st.info("Owner clarification received. Review the reply below before recording the next decision.")
        draft_suffix = f"{client_id}_{client['latest_decision']['id'] if client['latest_decision'] else 0}"
        owner_message = st.text_area(
            "Message to business owner",
            placeholder="Explain your decision or tell the owner exactly what needs clarification.",
            max_chars=1000,
            key=f"decision_owner_message_{draft_suffix}",
        )
        st.caption("Required for clarification. The owner can read this message in their portal.")
        note = st.text_area(
            "Internal advisor note",
            placeholder="Private context for the advisor team (optional)",
            max_chars=1000,
            key=f"decision_internal_note_{draft_suffix}",
        )
        accept, reject, clarify = st.columns(3)
        for column, label, decision, kind in (
            (accept, "ACCEPT REPRESENTATION", "accepted", "primary"),
            (reject, "REJECT DEAL", "rejected", "secondary"),
            (clarify, "REQUEST CLARIFICATION", "clarification", "secondary"),
        ):
            if column.button(label, key=f"action_{decision}", type=kind, use_container_width=True):
                try:
                    record_decision(
                        client_id, user["id"], user["firm_id"], decision,
                        note=note, owner_message=owner_message,
                    )
                except ValueError as exc:
                    st.error(str(exc))
                else:
                    st.session_state.decision_notice = "Decision saved. The owner portal now shows this update."
                    st.rerun()
        section_label("DECISION HISTORY")
        history = decision_history(client_id, user["firm_id"])
        if not history:
            st.info("No decisions have been recorded for this client.")
        for item in history:
            with st.container(border=True):
                st.markdown(f"**{item['decision'].replace('_', ' ').title()}**  /  {item['decided_at']} UTC")
                st.caption(f"Recorded by {item['advisor_name']}")
                if item["owner_message"]:
                    st.markdown("**Shown to owner**")
                    st.write(item["owner_message"])
                if item["note"]:
                    st.markdown("**Internal note**")
                    st.write(item["note"])
                if item["reply_message"]:
                    st.markdown(f"**Owner reply**  /  {item['replied_at']} UTC")
                    st.write(item["reply_message"])



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
    html('<div class="wizard-context"><span>ANSWER FOR TODAY</span>'
         '<p>Choose the option that best reflects the business as it operates now. '
         'Your responses are saved when you submit the full assessment.</p></div>')
    segments = "".join(
        f'<span class="{"done" if index < step else "current" if index == step else "upcoming"}"></span>'
        for index in range(len(questions))
    )
    html(
        f'<div class="question-progress-head"><span>ASSESSMENT PROGRESS</span>'
        f'<b>{step + 1:02d} / {len(questions):02d}</b></div>'
        f'<div class="question-progress" role="progressbar" aria-label="Assessment progress" '
        f'aria-valuemin="0" aria-valuemax="{len(questions)}" aria-valuenow="{step + 1}">'
        f'{segments}</div>'
    )
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


def render_owner_status(user: dict, client: dict) -> None:
    """Show the persisted advisor state and any action available to the owner."""
    decision = client["latest_decision"]
    if decision is None:
        label, tone = "AWAITING ADVISOR REVIEW", "awaiting"
        description = "Your assessment is with the advisor. Check here for their next update."
    elif decision["decision"] == "accepted":
        label, tone = "REPRESENTATION ACCEPTED", "accepted"
        description = "The advisor has marked your business as accepted for representation. Connect with them to discuss next steps."
    elif decision["decision"] == "rejected":
        label, tone = "NOT MOVING FORWARD", "rejected"
        description = "The advisor has decided not to move forward with representation at this time."
    elif decision["reply_message"]:
        label, tone = "CLARIFICATION SENT", "received"
        description = "Your response is recorded. The advisor can review it and update the decision."
    else:
        label, tone = "CLARIFICATION REQUESTED", "clarification"
        description = "The advisor needs more information. Reply below to keep the review moving."

    final = decision is not None and decision["decision"] in {"accepted", "rejected"}
    details = (
        ("Business profile", "Complete", "done"),
        ("Assessment", "Submitted", "done"),
        ("Advisor review", "Complete" if final else "In progress", "done" if final else "current"),
        ("Outcome", "Recorded" if final else "Pending", "done" if final else "upcoming"),
    )
    steps = "".join(
        f'<li class="owner-flow-step {state}"><span>{index:02d}</span>'
        f'<strong>{title}</strong><small>{detail}</small></li>'
        for index, (title, detail, state) in enumerate(details, start=1)
    )
    updated = f'LAST UPDATE / {escape(decision["decided_at"])} UTC' if decision else "LAST UPDATE / ASSESSMENT SUBMITTED"
    html(
        f'<section class="owner-status {tone}" aria-label="Advisor update" aria-live="polite">'
        '<div class="owner-status-top"><span>ADVISOR UPDATE</span>'
        f'<span>{updated}</span></div>'
        f'<div class="owner-status-title">{label}</div>'
        f'<p>{escape(description)}</p>'
        + (f'<div class="owner-message"><span>MESSAGE FROM ADVISOR</span>'
           f'<p>{escape(decision["owner_message"])}</p></div>'
           if decision and decision["owner_message"] else "")
        + '<ol class="owner-flow">' + steps + '</ol></section>'
    )
    st.button("CHECK FOR UPDATES", key="owner_refresh")
    st.caption("Advisor updates appear here when you sign in or check for updates.")

    if decision and decision["decision"] == "clarification" and not decision["reply_message"]:
        with st.form("clarification_reply", clear_on_submit=True):
            reply = st.text_area(
                "Reply to the advisor", max_chars=2000,
                placeholder="Answer the advisor's question or explain the missing detail.",
            )
            if st.form_submit_button("SEND CLARIFICATION", type="primary"):
                try:
                    respond_to_clarification(user["id"], reply)
                except ValueError as exc:
                    st.error(str(exc))
                else:
                    st.rerun()
    elif decision and decision["decision"] == "clarification" and decision["reply_message"]:
        st.success("Your clarification was sent to the advisor.")

    updates = business_decision_history(user["id"])
    if updates:
        with st.expander(f"UPDATE HISTORY / {len(updates)} ADVISOR UPDATE(S)"):
            for item in updates:
                with st.container(border=True):
                    title = {
                        "accepted": "Representation accepted",
                        "rejected": "Not moving forward",
                        "clarification": "Clarification requested",
                    }[item["decision"]]
                    st.markdown(f"**{title}**  /  {item['decided_at']} UTC")
                    if item["owner_message"]:
                        st.write(item["owner_message"])
                    if item["reply_message"]:
                        st.markdown(f"**Your reply**  /  {item['replied_at']} UTC")
                        st.write(item["reply_message"])


def render_owner_result(user: dict, client: dict) -> None:
    band = score_band(client["score"])
    color = band_class(band)
    messages = {
        "High": "Your answers show strong readiness across the ten vetting signals.",
        "Medium": "Your answers show a mixed profile with some areas to strengthen.",
        "Low": "Several readiness areas may need attention before a sale process.",
    }
    html('<div class="eyebrow">BUSINESS OWNER / PRIVATE RESULT</div>')
    st.title(client["business_name"])
    st.caption("Your readiness result and advisor updates, in one clear view.")
    overview, answers = st.tabs(["YOUR DASHBOARD", "YOUR ANSWERS"])
    with overview:
        html(
            f'<div class="owner-result {color}"><div class="card-label">OVERALL SALE READINESS</div>'
            f'<div class="owner-result-band {color}">{band.upper()}</div>'
            f'<p>{escape(messages[band])}</p><div class="result-meta">10 / 10 ANSWERS SUBMITTED</div></div>'
        )
        render_owner_status(user, client)
        section_label("ABOUT THIS RESULT")
        st.caption(
            "Your answers are available for advisor review. Readiness is a starting point "
            "for a conversation, not a valuation or promise of a sale."
        )
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
        render_owner_result(user, client)
    else:
        render_owner_wizard(user, client)
