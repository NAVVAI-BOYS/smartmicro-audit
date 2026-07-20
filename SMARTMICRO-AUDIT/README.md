# smartmicro Detection Modernisation Check

Lead magnet web app built by Navvai. Same architecture as AUDIT-LITE.

## What it is
An 11 question check for traffic engineers, mobility departments and highway
operators. Deterministic scoring runs entirely in the browser; the Flask
backend stores leads, tracks funnel events, and adds AI narrative polish with
a full client side fallback so nothing ever renders blank.

Combines five concepts in one flow: readiness health check, loop replacement
cost calculator, honest four technology selector, decisions versus data gap
finder, and privacy exposure check. Report follows the six numbered parts
structure: Verdict, Cost, Exposure, Map, Plan, Receipts.

## Deploy to Render
1. Push this repo to GitHub (suggested: NAVVAI-BOYS/SMARTMICRO-AUDIT).
2. New Web Service on Render, connect the repo.
3. Root Directory: smartmicro-audit
4. Build command: pip install -r requirements.txt
5. Start command: gunicorn app:app
6. Environment variables:
   - ANTHROPIC_API_KEY  (optional, enables AI narrative; fallback works without it)
   - ADMIN_KEY          (required for /api/leads.csv and /api/events)
   - CONTACT_EMAIL      (defaults to info@smartmicro.de)

## Routes
- /                          the app
- /?mode=consultant          no email gate, for live discovery calls
- /api/leads.csv?key=KEY     lead export
- /api/events?key=KEY        funnel events

## Notes
- Money maths uses only the prospect's own figures; skipped figures hide the
  section rather than inventing numbers.
- Verdict is computed from the weakest pillar (7+/4-6.9/<4) and the rule is
  printed in the report. The AI prompt enforces the same rule.
- Leads land in data/leads.json and Render logs.
