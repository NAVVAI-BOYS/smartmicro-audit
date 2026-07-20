import json
import os
import csv
import io
from datetime import datetime, timezone

from flask import Flask, jsonify, render_template, request, Response

try:
    import anthropic
    _HAS_ANTHROPIC = True
except Exception:
    _HAS_ANTHROPIC = False

app = Flask(__name__)

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
LEADS_FILE = os.path.join(DATA_DIR, "leads.json")
EVENTS_FILE = os.path.join(DATA_DIR, "events.json")
ADMIN_KEY = os.environ.get("ADMIN_KEY", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
CONTACT_EMAIL = os.environ.get("CONTACT_EMAIL", "info@smartmicro.de")
MODEL = os.environ.get("MODEL", "claude-sonnet-4-6")


def _ensure_data_dir():
    os.makedirs(DATA_DIR, exist_ok=True)


def _append_json_line(path, record):
    _ensure_data_dir()
    records = []
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                records = json.load(f)
        except Exception:
            records = []
    records.append(record)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2)


@app.route("/")
def index():
    return render_template("index.html", contact_email=CONTACT_EMAIL)


@app.route("/api/lead", methods=["POST"])
def lead():
    body = request.get_json(silent=True) or {}
    record = {
        "date": datetime.now(timezone.utc).isoformat(),
        "email": body.get("email", ""),
        "first_name": body.get("first_name", ""),
        "last_name": body.get("last_name", ""),
        "organisation": body.get("organisation", ""),
        "role": body.get("role", ""),
        "region": body.get("region", ""),
        "verdict": body.get("verdict", ""),
        "headline": body.get("headline", ""),
    }
    _append_json_line(LEADS_FILE, record)
    print(f"[lead] {record['email']} | {record['organisation']} | {record['verdict']}")
    return jsonify({"ok": True})


@app.route("/api/leads.csv")
def leads_csv():
    if not ADMIN_KEY or request.args.get("key") != ADMIN_KEY:
        return Response("Not authorised", status=403)
    records = []
    if os.path.exists(LEADS_FILE):
        with open(LEADS_FILE, "r", encoding="utf-8") as f:
            records = json.load(f)
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(["date", "email", "first_name", "last_name", "organisation",
                     "role", "region", "verdict", "headline"])
    for r in records:
        writer.writerow([r.get(k, "") for k in
                         ["date", "email", "first_name", "last_name", "organisation",
                          "role", "region", "verdict", "headline"]])
    return Response(out.getvalue(), mimetype="text/csv")


@app.route("/api/event", methods=["POST"])
def event():
    body = request.get_json(silent=True) or {}
    record = {
        "date": datetime.now(timezone.utc).isoformat(),
        "event": body.get("event", ""),
        "detail": body.get("detail", ""),
    }
    _append_json_line(EVENTS_FILE, record)
    print(f"[event] {record['event']} {record['detail']}")
    return jsonify({"ok": True})


@app.route("/api/events")
def events():
    if not ADMIN_KEY or request.args.get("key") != ADMIN_KEY:
        return Response("Not authorised", status=403)
    records = []
    if os.path.exists(EVENTS_FILE):
        with open(EVENTS_FILE, "r", encoding="utf-8") as f:
            records = json.load(f)
    return jsonify(records)


ANALYSIS_PROMPT = """You are writing the narrative sections of a Detection Modernisation Check report for a traffic professional. The scoring is already computed. Your job is narrative only. Respond with JSON and nothing else, no preamble, no markdown fences.

Rules, all mandatory:
- UK English. Plain language. No em dashes. No hyphens in compound modifiers where avoidable. No exclamation marks. No jargon without a plain explanation in the same sentence.
- Never invent money figures. The only money numbers you may reference are the ones supplied below, and always say they come from the reader's own figures.
- The verdict is computed from the weakest pillar and must not be contradicted: weakest pillar 7 or above means Ready to pilot, 4 to 6.9 means Plan the pilot, below 4 means Foundations first.
- Reference pillar names across sections so the report reads as one connected argument, not separate blocks.
- Every claim carries its reason in plain English.
- Be honest. If cameras or another technology genuinely serve one of the reader's stated needs better, say so. Balanced verdicts earn trust.

Context about the reader:
{context}

Computed results:
{results}

Return JSON with exactly these keys:
- "exec_summary": 3 sentences. What their situation is, what the verdict means for them, what the single next move is. Reference their 12 month goal in their own words.
- "blind_spot": 2 sentences naming one specific thing this reader is likely not seeing, grounded in their answers.
- "phase_notes": array of 3 strings, one sentence each, personalising phases 1 to 3 of the 90 day plan to their stated goal and weakest pillar.
"""


@app.route("/api/analyze", methods=["POST"])
def analyze():
    body = request.get_json(silent=True) or {}
    context = body.get("context", {})
    results = body.get("results", {})

    if not (_HAS_ANTHROPIC and ANTHROPIC_API_KEY):
        return jsonify({"ok": False, "reason": "no_api"})

    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        prompt = ANALYSIS_PROMPT.format(
            context=json.dumps(context, indent=2),
            results=json.dumps(results, indent=2),
        )
        started = datetime.now(timezone.utc)
        message = client.messages.create(
            model=MODEL,
            max_tokens=1200,
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(block.text for block in message.content if block.type == "text")
        duration = (datetime.now(timezone.utc) - started).total_seconds()
        print(f"[ai] {duration:.1f}s stop={message.stop_reason} chars={len(text)}")
        text = text.strip()
        if text.startswith("```"):
            text = text.strip("`")
            if text.startswith("json"):
                text = text[4:]
        parsed = json.loads(text)
        return jsonify({"ok": True, "narrative": parsed})
    except Exception as exc:  # noqa: BLE001
        print(f"[ai-error] {exc}")
        return jsonify({"ok": False, "reason": str(exc)})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
