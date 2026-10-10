# APEX: 2-Minute Loom Script

**Audience:** Salesforce/Agentforce customers, B2B sales leaders, brokerage owners.
**Goal of the video:** show that we can turn CRM data into risk alerts and an account plan, then ask for a call.
**Length:** about 2:00 (roughly 300 spoken words). Times are cumulative.

---

## Before you hit record

- [ ] `docker compose up --build` is running. Open http://localhost:3000 and confirm the dashboard loads.
- [ ] **`OPENROUTER_API_KEY` is set and the account has credit.** A Northwind plan takes about 45 seconds (8 model calls, a fraction of a cent).
- [ ] Run the Northwind question once before recording. The first run warms the models; the recorded run is then quicker.
- [ ] Browser at 100% zoom, 1440×900 or larger, bookmarks bar hidden, notifications off.
- [ ] Be signed out so the recording starts on the sign-in screen.
- [ ] The plan takes about 45 seconds. Cut the wait in editing; don't fill it with talk.

---

## Script

### 0:00–0:15 · The problem (landing page)
**On screen:** landing page, slow scroll.

> "If you run a B2B sales team, your CRM already knows which deals are about to slip: the renewal with one contact, the deal nobody has touched in three months, the support ticket the CFO is angry about. The problem is nobody has time to dig that out account by account. So we built APEX."

### 0:15–0:30 · Sign in (sign-in screen)
**On screen:** click **Use demo account**, then **Sign In**.

> "This is running on a demo CRM: sixteen fictional accounts with deals, contacts, activities and support cases, the same objects you have in Salesforce."

### 0:30–0:55 · Dashboard: what's at risk
**On screen:** dashboard. Hover the KPI strip, then the **Account Health** list, then **Risk Detection**.

> "First thing you see: open pipeline, average health, and how many accounts are critical. The health score isn't a guess. It's calculated from five things: pipeline, contact coverage, engagement, deal progress and support."
>
> "On the right, APEX has already found the risks. Northwind Logistics: two open critical support cases, and a one-point-two-million-dollar renewal where we only know one person."

### 0:55–1:35 · AI account plan
**On screen:** click the **Northwind Logistics** risk card. The Intelligence page opens and the plan starts generating. Scroll through it as it arrives.

> "One click, and APEX writes the account plan. Notice it's specific: it names Marcus Hale, our only contact. It knows procurement asked for a fifteen percent discount and that the VP of Operations hasn't been involved. It ties the support escalation to the renewal risk, and gives a dated action plan."
>
> "The model only gets this account's CRM records as context, and a grounding check scores how much of the answer matches those records. You review it before anything goes to a customer."

### 1:35–1:50 · Persona switch (optional, skip if short on time)
**On screen:** switch the toggle from **AM** to **VP Sales** and ask "Summarise Northwind for my VP".

> "Same data, different audience: a VP gets the short version with the revenue at stake."

### 1:50–2:00 · Close
**On screen:** back to the dashboard.

> "We built this ourselves, end to end. Now we implement the same thing on your Salesforce, with Agentforce or a custom build. If you want to see it on your own pipeline, book a call with Dataosis at dataosis.in."

---

## Things not to say
- Don't quote win-rate, revenue or time-saved numbers. We have no client results yet.
- Don't call it "production" or say "used by teams". It's a demo built on fictional data.
- Don't claim it's native Agentforce. It's a standalone app that shows what we'd build in your Salesforce.
