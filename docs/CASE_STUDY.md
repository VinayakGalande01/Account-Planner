# Case Study: APEX, an AI Co-pilot for Account Planning

*Built by [Dataosis AI](https://dataosis.in). A working demo on fictional CRM data, built to show what we deliver on Salesforce and Agentforce.*

---

## The problem

Sales teams lose renewals and expansions they could have saved. The warning signs are usually already in the CRM: a large deal with only one contact, an opportunity nobody has touched in months, a critical support case the customer's finance team is angry about.

These signals sit in separate objects (Opportunities, Contacts, Activities, Cases). To see them, an account manager has to open each account and piece the story together by hand. Most weeks nobody has time, so the risk shows up when the deal slips.

## The solution

APEX reads the CRM and does that work automatically:

1. **Scores every account's health (0–100)** from five factors: pipeline relative to business already won, contact coverage, engagement recency, deal progression, and support quality.
2. **Flags risks** with deterministic rules: open critical cases, single-threaded deals, stalled strategic accounts, deals past their close date, and low CSAT.
3. **Writes an account plan on request.** The user clicks a flagged account or asks in plain English. An AI pipeline pulls only that account's records, reasons about them, and returns a plan with named contacts, the revenue at stake and dated next steps. The plan is tailored to an Account Manager, a VP of Sales or an executive.
4. **Checks its own answer.** A grounding score measures how much of the plan matches actual CRM values, and a calculation auditor itemises pipeline totals.

**Stack:** FastAPI, Next.js, PostgreSQL (Supabase-compatible), ChromaDB retrieval over activity notes, and an LLM via OpenRouter (Gemini 2.5 Flash-Lite by default), with an Ollama option for fully local deployments. Everything ships with Docker Compose.

## The result (what the demo shows)

On a seeded book of 16 fictional accounts, APEX:

- **Ranks the portfolio by health** and puts the three critical accounts (score below 30) at the top of the dashboard.
- **Flags the Northwind Logistics renewal ($1.2M)** for its three risk signals: only one known contact, two open critical support cases, and a close date already passed.
- **Produces a Northwind account plan** that names the single champion, picks up the 15% discount request and the missing VP of Operations from the meeting notes, and lays out who to contact, when, and why.
- **Separates real risk from noise.** Healthy accounts with active, multi-threaded deals are not flagged.

> These results come from fictional demo data. APEX has not yet been deployed with a client, so we make no claims about win rates or time saved.

## What this means for your team

The same pattern runs inside your Salesforce org: Agentforce actions or a custom Lightning app on top of your real Opportunities, Contacts and Cases, with your own risk rules. A typical engagement starts by connecting to your sandbox and running the risk scan on your current pipeline.

**Talk to us:** [dataosis.in](https://dataosis.in)
