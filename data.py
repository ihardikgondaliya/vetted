"""Question bank transcribed from the supplied vetting workbook.

Wording is lightly edited for spelling and readability; answer meanings and
the workbook's High / Medium / Low order are preserved.
"""

QUESTIONS = (
    {
        "key": "team_execution",
        "prompt": "Can employees execute and make decisions without the owner, or is the owner heavily involved in delivery?",
        "high": "Employees are self-sufficient.",
        "medium": "Employees need guidance in some areas but work independently.",
        "low": "Employees need consistent owner guidance and input.",
    },
    {
        "key": "owner_sales_reliance",
        "prompt": "How dependent are sales on the owner rather than the company and its sales team?",
        "high": "A self-sufficient sales team delivers results without the owner.",
        "medium": "The sales team delivers results together with the owner.",
        "low": "Sales depend completely on the owner.",
    },
    {
        "key": "relationship_ownership",
        "prompt": "When a customer signs and is onboarded, who owns the relationship?",
        "high": "Delivery and account management teams own customer relationships.",
        "medium": "The owner and team share customer relationships.",
        "low": "The owner owns customer relationships.",
    },
    {
        "key": "financial_quality",
        "prompt": "What is the quality of the financial statements?",
        "high": "Financial statements receive a CPA review.",
        "medium": "An established accounting firm prepares statements, without CPA review.",
        "low": "Statements are prepared internally or by an independent consultant.",
    },
    {
        "key": "revenue_growth",
        "prompt": "What does the revenue growth trend look like?",
        "high": "Revenue is growing.",
        "medium": "Revenue is stable or fluctuating without a clear growth trend.",
        "low": "Revenue is declining.",
    },
    {
        "key": "customer_concentration",
        "prompt": "What percentage of revenue comes from the top three customers?",
        "high": "Less than 15% of revenue.",
        "medium": "15% to 30% of revenue.",
        "low": "More than 30% of revenue.",
    },
    {
        "key": "key_person_risk",
        "prompt": "How many people leaving next month would seriously hurt the business?",
        "high": "None.",
        "medium": "One or two executives or other key employees.",
        "low": "Several people across the organization.",
    },
    {
        "key": "legal_cleanliness",
        "prompt": "Are there liens, lawsuits, unpaid taxes, disputed ownership, or handshake deals with partners?",
        "high": "No such issues.",
        "medium": "There were issues historically, but they are resolved.",
        "low": "One or more issues remain open.",
    },
    {
        "key": "asset_ownership",
        "prompt": "Are the brand, IP, software, licenses, vehicles, and property legally owned by the company?",
        "high": "Yes, all critical assets are company-owned.",
        "medium": "Some critical assets still need formal assignment to the company.",
        "low": "No, critical assets are not legally owned by the company.",
    },
    {
        "key": "process_transferability",
        "prompt": "Could a new owner quickly understand and run the business from documented processes?",
        "high": "Yes, processes and knowledge are documented and fully transferable.",
        "medium": "Processes are partly documented and transferable.",
        "low": "Processes are not yet transferable.",
    },
)

DEMO_CLIENTS = (
    {
        "name": "Northstar Industrial Components",
        "industry": "Industrial Manufacturing",
        "annual_revenue": 18_400_000,
        "owner_email": "northstar@vetted.demo",
        "owner_name": "Jordan Ellis",
        "ratings": ("high", "high", "medium", "high", "high", "high", "high", "high", "medium", "high"),
        "decision": "accepted",
    },
    {
        "name": "Harborlight Health Services",
        "industry": "Healthcare Services",
        "annual_revenue": 7_200_000,
        "owner_email": "harborlight@vetted.demo",
        "owner_name": "Morgan Patel",
        "ratings": ("medium", "medium", "medium", "high", "medium", "medium", "medium", "high", "medium", "medium"),
        "decision": None,
    },
    {
        "name": "Cedar Ridge Specialty Foods",
        "industry": "Food & Beverage",
        "annual_revenue": 4_800_000,
        "owner_email": "cedar@vetted.demo",
        "owner_name": "Taylor Brooks",
        "ratings": ("low", "low", "low", "medium", "low", "low", "medium", "low", "medium", "low"),
        "decision": "clarification",
    },
)
