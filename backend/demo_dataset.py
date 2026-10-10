"""
DEMO CRM DATASET (demo_dataset.py)
Deterministic, fictional CRM data used to seed APEX for demos and local development.
All company names, people, emails (*.example) and phone numbers (555-01xx) are invented.
Dates are generated relative to "today" so the risk scenarios never go stale.

Usage:
    python demo_dataset.py            # writes demo_crm_data.xlsx next to this file
    build_demo_sheets()               # returns {sheet_name: DataFrame} for the sync loader
"""

# --- SECTION 1: Dependencies & Imports ---
from datetime import date, timedelta
import os
import pandas as pd

DEMO_XLSX_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "demo_crm_data.xlsx")

# --- SECTION 2: Account Scenarios ---
# Each account is written as a story. Offsets are in days relative to today
# (negative = past). `health` is the stored CRM health score used by the risk radar.
#
# (id, name, industry, tier, territory, country, revenue_usd, health)
ACCOUNTS = [
    # --- At-risk accounts (the demo's main characters) ---
    ("ACC001", "Northwind Logistics",       "Logistics",       "Strategic", "North America", "US", 840_000_000, 28),
    ("ACC002", "Meridian Health Network",   "Healthcare",      "Strategic", "North America", "US", 1_250_000_000, 41),
    ("ACC003", "Crestline Realty Group",    "Real Estate",     "Key",       "EMEA",          "GB", 310_000_000, 38),
    ("ACC004", "Halvorsen Retail Co.",      "Retail",          "Key",       "EMEA",          "NO", 520_000_000, 23),
    ("ACC005", "Sablewood Manufacturing",   "Manufacturing",   "Normal",    "APAC",          "IN", 190_000_000, 14),
    # --- Healthy / growing accounts ---
    ("ACC006", "Brightwater Capital",       "Financial Services", "Strategic", "North America", "US", 2_100_000_000, 88),
    ("ACC007", "Orion BioLabs",             "Life Sciences",   "Key",       "North America", "CA", 430_000_000, 82),
    ("ACC008", "Atlas Property Partners",   "Real Estate",     "Key",       "APAC",          "SG", 275_000_000, 79),
    ("ACC009", "Keystone Mutual Insurance", "Insurance",       "Strategic", "North America", "US", 1_600_000_000, 74),
    ("ACC010", "Lumen Fiber Networks",      "Telecommunications", "Key",    "LATAM",         "BR", 680_000_000, 71),
    ("ACC011", "Pinecrest Hospitality",     "Hospitality",     "Normal",    "EMEA",          "AE", 145_000_000, 77),
    ("ACC012", "Cobalt Grid Energy",        "Energy",          "Key",       "EMEA",          "DE", 950_000_000, 69),
    ("ACC013", "Redwood Learning Trust",    "Education",       "Normal",    "North America", "US", 85_000_000, 83),
    ("ACC014", "Bluefin Media Studios",     "Media",           "Normal",    "APAC",          "AU", 120_000_000, 36),
    ("ACC015", "Sterling & Vane Legal",     "Professional Services", "Normal", "EMEA",      "GB", 98_000_000, 80),
    ("ACC016", "Vantage Freight Systems",   "Logistics",       "Key",       "South Asia",    "IN", 360_000_000, 72),
]

# (opp_id, acc, name, stage, amount, close_offset, prob, product, competitor, owner, created_offset)
OPPORTUNITIES = [
    # Northwind: $1.2M renewal stuck in negotiation, 21 days past close date, single champion.
    ("OPP001", "ACC001", "Northwind - Fleet Analytics Renewal",  "Negotiation/Review",   1_200_000, -21, 60, "Analytics Platform", "Competitor A", "Priya Nair", -160),
    ("OPP002", "ACC001", "Northwind - Route Optimisation Add-on", "Proposal/Price Quote",  340_000, -95, 40, "Optimisation Module", "Competitor B", "Priya Nair", -200),
    ("OPP003", "ACC001", "Northwind - Warehouse IoT Pilot",       "Closed Lost",           180_000, -120, 0, "IoT Suite", "Competitor A", "Priya Nair", -260),
    # Meridian: big expansion that has gone quiet; stale for 100+ days.
    ("OPP004", "ACC002", "Meridian - Patient Data Platform Expansion", "Proposal/Price Quote", 2_400_000, -110, 45, "Data Platform", "Competitor C", "Daniel Ortiz", -240),
    ("OPP005", "ACC002", "Meridian - Clinical Reporting Seats",   "Value Proposition",     260_000, 35, 30, "Reporting Seats", None, "Daniel Ortiz", -60),
    ("OPP006", "ACC002", "Meridian - FY Platform Licence",        "Closed Won",          1_100_000, -300, 100, "Platform Licence", None, "Daniel Ortiz", -420),
    # Crestline Realty: brokerage pipeline under threat from support escalations.
    ("OPP007", "ACC003", "Crestline - Deal Pipeline CRM Rollout",  "Negotiation/Review",    480_000, 14, 55, "CRM Rollout", "Competitor B", "Hannah Weiss", -90),
    ("OPP008", "ACC003", "Crestline - Listing Data Integration",   "Closed Lost",           150_000, -60, 0, "Integration Services", "Competitor B", "Hannah Weiss", -180),
    # Halvorsen Retail: most recent deals lost to a competitor.
    ("OPP009", "ACC004", "Halvorsen - Store Forecasting",          "Closed Lost",           620_000, -45, 0, "Forecasting Suite", "Competitor C", "Hannah Weiss", -210),
    ("OPP010", "ACC004", "Halvorsen - Loyalty Analytics",          "Closed Lost",           210_000, -15, 0, "Loyalty Analytics", "Competitor C", "Hannah Weiss", -150),
    ("OPP011", "ACC004", "Halvorsen - Inventory Sync",             "Qualification",         190_000, 75, 20, "Inventory Sync", "Competitor C", "Hannah Weiss", -20),
    # Sablewood: no named decision maker, engagement decaying.
    ("OPP012", "ACC005", "Sablewood - Plant Quality Dashboards",   "Id. Decision Makers",   230_000, 40, 25, "Quality Dashboards", None, "Arjun Mehta", -70),
    # Healthy accounts
    ("OPP013", "ACC006", "Brightwater - Risk Analytics Expansion", "Negotiation/Review",  1_850_000, 18, 80, "Risk Analytics", "Competitor A", "Daniel Ortiz", -120),
    ("OPP014", "ACC006", "Brightwater - Advisor Workspace",        "Closed Won",            900_000, -40, 100, "Advisor Workspace", None, "Daniel Ortiz", -180),
    ("OPP015", "ACC006", "Brightwater - Compliance Reporting",     "Proposal/Price Quote",  540_000, 45, 60, "Compliance Reporting", None, "Daniel Ortiz", -50),
    ("OPP016", "ACC007", "Orion - Lab Data Lake",                  "Proposal/Price Quote",  720_000, 30, 65, "Data Lake", "Competitor C", "Priya Nair", -75),
    ("OPP017", "ACC007", "Orion - Trial Ops Automation",           "Closed Won",            380_000, -25, 100, "Automation Suite", None, "Priya Nair", -140),
    ("OPP018", "ACC008", "Atlas - Portfolio Deal Tracker",         "Negotiation/Review",    410_000, 21, 75, "Deal Tracker", None, "Arjun Mehta", -80),
    ("OPP019", "ACC008", "Atlas - Tenant Portal",                  "Closed Won",            260_000, -70, 100, "Tenant Portal", None, "Arjun Mehta", -190),
    ("OPP020", "ACC009", "Keystone - Claims Triage AI",            "Value Proposition",   1_300_000, 60, 40, "Claims Triage", "Competitor A", "Daniel Ortiz", -45),
    ("OPP021", "ACC009", "Keystone - Agent Analytics Renewal",     "Closed Won",            820_000, -90, 100, "Agent Analytics", None, "Daniel Ortiz", -200),
    ("OPP022", "ACC010", "Lumen - Network Churn Prediction",       "Perception Analysis",   560_000, 50, 50, "Churn Prediction", "Competitor B", "Lucas Ferreira", -55),
    ("OPP023", "ACC010", "Lumen - Field Service Scheduling",       "Closed Won",            300_000, -110, 100, "Field Service", None, "Lucas Ferreira", -230),
    ("OPP024", "ACC011", "Pinecrest - Revenue Management",         "Proposal/Price Quote",  175_000, 28, 60, "Revenue Management", None, "Hannah Weiss", -40),
    ("OPP025", "ACC012", "Cobalt - Asset Health Monitoring",       "Needs Analysis",        870_000, 80, 30, "Asset Monitoring", "Competitor C", "Hannah Weiss", -30),
    ("OPP026", "ACC012", "Cobalt - Grid Ops Reporting",            "Closed Won",            450_000, -150, 100, "Ops Reporting", None, "Hannah Weiss", -260),
    ("OPP033", "ACC011", "Pinecrest - Guest Analytics",            "Closed Won",            120_000, -95, 100, "Guest Analytics", None, "Hannah Weiss", -200),
    ("OPP034", "ACC013", "Redwood - Enrollment Forecasting",       "Closed Won",             95_000, -130, 100, "Enrollment Forecasting", None, "Arjun Mehta", -240),
    ("OPP027", "ACC013", "Redwood - Student Success Analytics",    "Negotiation/Review",    140_000, 12, 85, "Student Analytics", None, "Arjun Mehta", -65),
    ("OPP028", "ACC014", "Bluefin - Audience Insights",            "Prospecting",           220_000, 90, 10, "Audience Insights", "Competitor B", "Arjun Mehta", -10),
    ("OPP029", "ACC015", "Sterling & Vane - Matter Intelligence",  "Closed Won",            160_000, -35, 100, "Matter Intelligence", None, "Hannah Weiss", -120),
    ("OPP030", "ACC015", "Sterling & Vane - Billing Automation",   "Value Proposition",     110_000, 55, 40, "Billing Automation", None, "Hannah Weiss", -25),
    ("OPP031", "ACC016", "Vantage - Shipment Visibility",          "Proposal/Price Quote",  390_000, 33, 60, "Shipment Visibility", "Competitor A", "Arjun Mehta", -60),
    ("OPP032", "ACC016", "Vantage - Carrier Scorecards",           "Closed Won",            150_000, -80, 100, "Carrier Scorecards", None, "Arjun Mehta", -170),
]

# (contact_id, acc, first, last, role, dept, engagement, last_contact_offset)
CONTACTS = [
    # Northwind: only ONE contact on a $1.2M deal -> single-threaded.
    ("CON001", "ACC001", "Marcus", "Hale",      "Champion",        "Operations", "Medium", -38),
    # Meridian: contacts exist but have gone cold.
    ("CON002", "ACC002", "Elena",  "Park",      "Decision Maker",  "IT",         "Low",    -82),
    ("CON003", "ACC002", "Tom",    "Becker",    "Technical Buyer", "IT",         "Low",    -95),
    # Crestline: champion engaged, but the CFO is frustrated by support issues.
    ("CON004", "ACC003", "Sofia",  "Laurent",   "Champion",        "Brokerage",  "High",   -6),
    ("CON005", "ACC003", "Graham", "Whitfield", "Decision Maker",  "Finance",    "Low",    -48),
    # Halvorsen
    ("CON006", "ACC004", "Ingrid", "Solberg",   "Influencer",      "Merchandising", "Medium", -20),
    ("CON007", "ACC004", "Erik",   "Dahl",      "Technical Buyer", "IT",         "Low",    -55),
    # Sablewood: no decision maker mapped.
    ("CON008", "ACC005", "Kavya",  "Rao",       "End User",        "Quality",    "Medium", -64),
    # Brightwater: well multi-threaded.
    ("CON009", "ACC006", "Olivia", "Chen",      "Decision Maker",  "Finance",    "High",   -3),
    ("CON010", "ACC006", "Jamal",  "Wright",    "Champion",        "Risk",       "High",   -5),
    ("CON011", "ACC006", "Hiro",   "Tanaka",    "Technical Buyer", "IT",         "High",   -9),
    ("CON012", "ACC006", "Rachel", "Moore",     "Influencer",      "Compliance", "Medium", -14),
    ("CON013", "ACC007", "Nadia",  "Fischer",   "Decision Maker",  "R&D",        "High",   -7),
    ("CON014", "ACC007", "Paul",   "Grant",     "Champion",        "Lab Ops",    "High",   -4),
    ("CON015", "ACC007", "Mei",    "Lin",       "Technical Buyer", "IT",         "Medium", -18),
    ("CON016", "ACC008", "Wei",    "Ong",       "Decision Maker",  "Investments","High",   -10),
    ("CON017", "ACC008", "Aisha",  "Rahman",    "Champion",        "Asset Mgmt", "High",   -6),
    ("CON018", "ACC008", "Daniel", "Koh",       "End User",        "Leasing",    "Medium", -22),
    ("CON019", "ACC009", "Laura",  "Bennett",   "Decision Maker",  "Claims",     "Medium", -16),
    ("CON020", "ACC009", "Chris",  "Doyle",     "Champion",        "Claims",     "High",   -8),
    ("CON021", "ACC009", "Sam",    "Patel",     "Technical Buyer", "IT",         "Medium", -25),
    ("CON022", "ACC010", "Bruno",  "Almeida",   "Decision Maker",  "Network",    "Medium", -19),
    ("CON023", "ACC010", "Camila", "Souza",     "Champion",        "Customer Experience", "High", -11),
    ("CON024", "ACC010", "Rafael", "Costa",     "Technical Buyer", "IT",         "Medium", -30),
    ("CON025", "ACC011", "Omar",   "Haddad",    "Decision Maker",  "Revenue",    "High",   -9),
    ("CON026", "ACC011", "Leila",  "Nasser",    "End User",        "Front Office","Medium", -21),
    ("CON027", "ACC011", "Yusuf",  "Karim",     "Influencer",      "Finance",    "Medium", -27),
    ("CON028", "ACC012", "Katrin", "Vogel",     "Decision Maker",  "Grid Ops",   "Medium", -24),
    ("CON029", "ACC012", "Jonas",  "Weber",     "Technical Buyer", "Engineering","High",   -12),
    ("CON030", "ACC012", "Lena",   "Schmidt",   "Champion",        "Asset Mgmt", "High",   -8),
    ("CON031", "ACC013", "Grace",  "Holloway",  "Decision Maker",  "Academics",  "High",   -5),
    ("CON032", "ACC013", "Ben",    "Ashford",   "Champion",        "IT",         "High",   -3),
    ("CON033", "ACC013", "Maya",   "Ellison",   "End User",        "Admissions", "Medium", -15),
    ("CON034", "ACC014", "Liam",   "Carter",    "Influencer",      "Marketing",  "Medium", -28),
    ("CON035", "ACC014", "Zoe",    "Mitchell",  "Decision Maker",  "Strategy",   "Low",    -41),
    ("CON036", "ACC014", "Noah",   "Reid",      "End User",        "Analytics",  "Medium", -20),
    ("CON037", "ACC015", "Charlotte", "Vane",   "Decision Maker",  "Partners",   "High",   -11),
    ("CON038", "ACC015", "Oliver", "Sterling",  "Champion",        "Operations", "High",   -6),
    ("CON039", "ACC015", "Amelia", "Hart",      "End User",        "Billing",    "Medium", -19),
    ("CON040", "ACC016", "Rohan",  "Kapoor",    "Decision Maker",  "Operations", "Medium", -13),
    ("CON041", "ACC016", "Sneha",  "Iyer",      "Champion",        "Logistics",  "High",   -7),
    ("CON042", "ACC016", "Vikram", "Joshi",     "Technical Buyer", "IT",         "Medium", -23),
]

# (case_id, acc, contact, subject, status, severity, open_offset, csat, root_cause)
CASES = [
    ("CASE001", "ACC001", "CON001", "Fleet dashboard data delayed by 6+ hours", "Escalated",   "Critical", -19, None, "Data pipeline backlog"),
    ("CASE002", "ACC001", "CON001", "SSO login failures for depot managers",    "Open",        "High",     -9,  None, "Identity provider config"),
    ("CASE003", "ACC002", "CON003", "HL7 feed intermittently dropping records", "In Progress", "High",     -27, None, "Integration defect"),
    ("CASE004", "ACC003", "CON005", "Commission report totals do not reconcile","Escalated",   "Critical", -12, None, "Calculation bug"),
    ("CASE005", "ACC003", "CON004", "Listing sync missing new properties",      "Open",        "High",     -5,  None, "Integration defect"),
    ("CASE006", "ACC003", "CON004", "Slow pipeline board load times",           "Closed",      "Medium",   -40, 2.8, "Performance"),
    ("CASE007", "ACC004", "CON007", "Forecast export times out",                "Closed",      "Medium",   -70, 3.1, "Performance"),
    ("CASE008", "ACC005", "CON008", "Dashboard filters reset on refresh",       "Open",        "Medium",   -22, None, "UI bug"),
    ("CASE009", "ACC006", "CON011", "Request: additional API rate limit",       "Closed",      "Low",      -30, 4.8, "Capacity request"),
    ("CASE010", "ACC007", "CON015", "Data lake connector setup question",       "Closed",      "Low",      -15, 4.6, "How-to"),
    ("CASE011", "ACC009", "CON021", "Claims model scoring latency",             "In Progress", "Medium",   -8,  None, "Performance"),
    ("CASE012", "ACC010", "CON024", "Field app offline sync conflict",          "Closed",      "Medium",   -45, 4.2, "Product bug"),
    ("CASE013", "ACC012", "CON029", "Sensor ingestion schema change",           "Closed",      "Low",      -60, 4.5, "Customer change"),
    ("CASE014", "ACC014", "CON036", "Audience segment export incomplete",       "Open",        "Medium",   -11, None, "Product bug"),
    ("CASE015", "ACC016", "CON042", "Carrier feed mapping update",              "Closed",      "Low",      -25, 4.7, "Configuration"),
]

# (acc, contact, opp, type, subject, offset, minutes, notes)
ACTIVITIES = [
    # Northwind: last real touch ~5 weeks ago; procurement silence.
    ("ACC001", "CON001", "OPP001", "Meeting",   "Renewal pricing review", -38, 60, "Marcus flagged that procurement wants a 15% discount and that the VP of Operations has not been involved yet."),
    ("ACC001", "CON001", "OPP001", "Email",     "Follow-up on renewal terms", -30, 10, "Sent revised renewal terms. No reply received."),
    ("ACC001", "CON001", None,     "Call",      "Escalation call on dashboard delays", -17, 25, "Marcus frustrated about delayed fleet data; said it is hurting his internal case for renewal."),
    ("ACC001", "CON001", "OPP002", "Email",     "Route optimisation proposal", -100, 10, "Proposal sent; champion said budget was frozen until next quarter."),
    # Meridian: nothing in 80+ days.
    ("ACC002", "CON002", "OPP004", "Meeting",   "Expansion business case", -82, 60, "Elena asked for a security review before taking the expansion to the board."),
    ("ACC002", "CON003", "OPP004", "Demo",      "Data platform technical demo", -95, 90, "Positive technical demo; open question on HL7 throughput."),
    ("ACC002", "CON002", "OPP006", "Meeting",   "Annual licence QBR", -150, 45, "Licence usage at 92%; expansion discussed."),
    # Crestline
    ("ACC003", "CON004", "OPP007", "Meeting",   "Rollout plan with brokerage leads", -6, 45, "Sofia confirmed 40 brokers ready to onboard if commission reporting is fixed."),
    ("ACC003", "CON005", "OPP007", "Call",      "CFO escalation on commission report", -11, 20, "Graham said he will not sign the rollout until the commission totals reconcile."),
    ("ACC003", "CON004", None,     "Email",     "Listing sync incident update", -4, 10, "Shared workaround for missing listings; fix ETA pending from engineering."),
    # Halvorsen
    ("ACC004", "CON006", "OPP009", "Meeting",   "Loss review - forecasting", -40, 45, "Ingrid said competitor offered native POS integration and a lower year-one price."),
    ("ACC004", "CON006", "OPP011", "Call",      "Inventory sync discovery", -20, 30, "Early interest in inventory sync; IT not yet engaged."),
    # Sablewood
    ("ACC005", "CON008", "OPP012", "Demo",      "Quality dashboards demo", -64, 60, "Kavya liked the dashboards but could not say who signs off on budget."),
    # Brightwater
    ("ACC006", "CON009", "OPP013", "Meeting",   "Commercial terms review", -3, 60, "Olivia approved budget; legal review of MSA in progress."),
    ("ACC006", "CON010", "OPP013", "Call",      "Implementation plan", -5, 30, "Jamal aligned on a 6-week rollout starting next month."),
    ("ACC006", "CON011", "OPP013", "Demo",      "Security architecture walkthrough", -9, 60, "Hiro signed off on the security questionnaire."),
    ("ACC006", "CON012", "OPP015", "Meeting",   "Compliance reporting scoping", -14, 45, "Rachel shared current regulatory reporting templates."),
    ("ACC006", "CON010", "OPP014", "Meeting",   "Advisor Workspace QBR", -28, 45, "Adoption at 87% of licensed advisors."),
    # Orion
    ("ACC007", "CON013", "OPP016", "Meeting",   "Data lake business case", -7, 60, "Nadia confirmed budget in next fiscal plan."),
    ("ACC007", "CON014", "OPP016", "Call",      "Pilot success criteria", -4, 30, "Paul drafted pilot success criteria with the lab ops team."),
    ("ACC007", "CON015", "OPP016", "Demo",      "Connector demo", -18, 60, "Mei validated connectors for three instrument systems."),
    # Atlas
    ("ACC008", "CON016", "OPP018", "Meeting",   "Deal tracker pricing", -10, 45, "Wei asked for a regional rollout option across 3 markets."),
    ("ACC008", "CON017", "OPP018", "Call",      "Rollout timeline", -6, 30, "Aisha confirmed asset managers want go-live before quarter end."),
    ("ACC008", "CON018", "OPP019", "Email",     "Tenant portal feedback", -22, 10, "Leasing team reports fewer tenant support tickets since launch."),
    # Keystone
    ("ACC009", "CON020", "OPP020", "Demo",      "Claims triage demo", -8, 60, "Chris impressed by triage accuracy on sample claims."),
    ("ACC009", "CON019", "OPP020", "Meeting",   "Claims triage business case", -16, 45, "Laura wants a cost-per-claim comparison before committing."),
    ("ACC009", "CON021", None,     "Call",      "Latency investigation", -7, 20, "Sam shared logs for the scoring latency case."),
    # Lumen
    ("ACC010", "CON023", "OPP022", "Meeting",   "Churn prediction workshop", -11, 90, "Camila mapped top three churn drivers with our team."),
    ("ACC010", "CON022", "OPP022", "Email",     "Workshop summary", -10, 10, "Sent workshop summary and next-step proposal to Bruno."),
    ("ACC010", "CON024", None,     "Call",      "Field app sync follow-up", -30, 15, "Confirmed fix for offline sync conflict."),
    # Pinecrest
    ("ACC011", "CON025", "OPP024", "Meeting",   "Revenue management proposal", -9, 45, "Omar requested a phased rollout across two properties first."),
    ("ACC011", "CON027", "OPP024", "Email",     "Pricing breakdown", -27, 10, "Shared pricing breakdown with finance."),
    # Cobalt
    ("ACC012", "CON030", "OPP025", "Meeting",   "Asset monitoring discovery", -8, 60, "Lena described 2 unplanned outages last quarter."),
    ("ACC012", "CON029", "OPP025", "Demo",      "Sensor data demo", -12, 60, "Jonas validated ingestion from existing SCADA exports."),
    ("ACC012", "CON028", "OPP026", "Meeting",   "Ops reporting QBR", -24, 45, "Katrin happy with reporting; open to wider asset monitoring."),
    # Redwood
    ("ACC013", "CON031", "OPP027", "Meeting",   "Final terms", -5, 30, "Grace confirmed board approval; contract out for signature."),
    ("ACC013", "CON032", "OPP027", "Call",      "SIS integration plan", -3, 30, "Ben confirmed student information system access."),
    # Bluefin
    ("ACC014", "CON034", "OPP028", "Call",      "Intro call", -28, 30, "Liam interested in audience insights; strategy lead not yet engaged."),
    ("ACC014", "CON036", None,     "Email",     "Segment export case", -11, 10, "Acknowledged export issue; fix scheduled."),
    # Sterling & Vane
    ("ACC015", "CON038", "OPP030", "Meeting",   "Billing automation scoping", -6, 45, "Oliver wants to cut month-end billing from 5 days to 2."),
    ("ACC015", "CON037", "OPP029", "Meeting",   "Matter intelligence QBR", -11, 45, "Charlotte sponsoring rollout to two more practice groups."),
    # Vantage
    ("ACC016", "CON041", "OPP031", "Demo",      "Shipment visibility demo", -7, 60, "Sneha shared lane data for a proof of value."),
    ("ACC016", "CON040", "OPP031", "Meeting",   "Commercial discussion", -13, 45, "Rohan asked for a regional pricing option."),
    ("ACC016", "CON042", None,     "Call",      "Carrier feed mapping", -23, 20, "Feed mapping updated and verified."),
]


# --- SECTION 3: Sheet Builder ---
def _slug(name: str) -> str:
    return "".join(ch for ch in name.lower().replace("&", "and").replace(" ", "-") if ch.isalnum() or ch == "-").strip("-")


def build_demo_sheets(today: date = None) -> dict:
    """Return {sheet_name: DataFrame} using the same schema as the Salesforce-style Excel export."""
    today = today or date.today()
    d = lambda offset: (today + timedelta(days=offset)).isoformat()
    domains = {a[0]: f"{_slug(a[1])}.example" for a in ACCOUNTS}

    accounts = pd.DataFrame([{
        "Account_ID": a, "Account_Name": n, "Industry": ind, "Annual_Revenue_USD": rev,
        "Territory": terr, "Account_Tier": tier, "Country": c, "Health_Score": float(h),
        "Website": f"www.{domains[a]}",
    } for a, n, ind, tier, terr, c, rev, h in ACCOUNTS])

    opps = pd.DataFrame([{
        "Opp_ID": o, "Account_ID": a, "Opp_Name": n, "Stage": st, "Amount_USD": amt,
        "Close_Date": d(close), "Probability_Pct": p, "Product": prod, "Competitor": comp,
        "Owner": owner, "Created_Date": d(created),
    } for o, a, n, st, amt, close, p, prod, comp, owner, created in OPPORTUNITIES])

    contacts = pd.DataFrame([{
        "Contact_ID": cid, "Account_ID": a, "First_Name": f, "Last_Name": l, "Role": role,
        "Email": f"{f.lower()}.{l.lower()}@{domains[a]}", "Phone": f"+1-555-01{i:02d}",
        "Engagement_Level": eng, "Last_Contact_Date": d(last), "Department": dept,
    } for i, (cid, a, f, l, role, dept, eng, last) in enumerate(CONTACTS)])

    cases = pd.DataFrame([{
        "Case_ID": cid, "Account_ID": a, "Contact_ID": con, "Subject": subj, "Status": st,
        "Severity": sev, "Open_Date": d(opened), "CSAT_Score": csat, "Root_Cause": rc,
    } for cid, a, con, subj, st, sev, opened, csat, rc in CASES])

    activities = pd.DataFrame([{
        "Activity_ID": f"ACT{i + 1:03d}", "Account_ID": a, "Contact_ID": con, "Opp_ID": opp,
        "Activity_Type": typ, "Subject": subj, "Activity_Date": d(offset), "Duration_Min": mins,
        "Status": "Completed", "Notes": notes,
    } for i, (a, con, opp, typ, subj, offset, mins, notes) in enumerate(ACTIVITIES)])

    return {"Account": accounts, "Opportunity": opps, "Contact": contacts, "Case": cases, "Activity": activities}


def write_demo_xlsx(path: str = DEMO_XLSX_PATH, today: date = None) -> str:
    with pd.ExcelWriter(path) as writer:
        for name, df in build_demo_sheets(today).items():
            df.to_excel(writer, sheet_name=name, index=False)
    return path


if __name__ == "__main__":
    out = write_demo_xlsx()
    sheets = build_demo_sheets()
    print(f"Wrote {out}: " + ", ".join(f"{len(v)} {k}" for k, v in sheets.items()))
