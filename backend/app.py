"""
Coffee Dial — Backend Server
Flask + SQLite backend for the Coffee Dial web app.

Endpoints:
  POST /api/parse-bag       — AI-powered bag text parsing (OpenAI or Anthropic)
  POST /api/search-coffee   — Search for a coffee by name using AI
  GET  /api/history         — Fetch brew history
  POST /api/history         — Save a brew entry
  PUT  /api/history/<id>    — Update a brew entry (e.g. add rating)
  DELETE /api/history/<id>  — Delete a brew entry
  GET  /api/presets         — Get household brew presets
  POST /api/presets         — Save a brew preset
  DELETE /api/presets/<id>  — Delete a preset
  POST /api/push-aiden      — Push a profile to Fellow Aiden
  GET  /api/settings        — Get settings (masked credentials)
  POST /api/settings        — Save settings (API keys, Fellow creds)
"""

import os
import json
import sqlite3
import time
import re
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

DB_PATH = os.environ.get("COFFEE_DIAL_DB", os.path.join(os.path.dirname(__file__), "coffee_dial.db"))
SETTINGS_PATH = os.path.join(os.path.dirname(__file__), "settings.json")


# ─── Database setup ───────────────────────────────────────────────────────────

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS brews (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp   INTEGER NOT NULL,
                bag_text    TEXT,
                coffee_name TEXT,
                roast       TEXT,
                origin      TEXT,
                process     TEXT,
                roaster     TEXT,
                grind       REAL,
                temp_c      REAL,
                ratio       REAL,
                bloom_dur   INTEGER,
                bloom_ratio REAL,
                pulses      INTEGER,
                pulse_int   INTEGER,
                brew_oz     REAL,
                brew_grams  REAL,
                preset_name TEXT,
                rating      TEXT,
                notes       TEXT,
                rationale   TEXT
            );

            CREATE TABLE IF NOT EXISTS presets (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT NOT NULL UNIQUE,
                oz          REAL NOT NULL,
                grams       REAL NOT NULL,
                sort_order  INTEGER DEFAULT 0
            );

            INSERT OR IGNORE INTO presets (name, oz, grams, sort_order) VALUES
                ('Taylor (12.5oz)', 12.5, 22.0, 0),
                ('Wife (14oz)',     14.0, 24.5, 1),
                ('Batch (30oz)',    30.0, 52.0, 2);
        """)

init_db()


# ─── Settings ─────────────────────────────────────────────────────────────────

def load_settings():
    if os.path.exists(SETTINGS_PATH):
        with open(SETTINGS_PATH) as f:
            return json.load(f)
    return {}

def save_settings_file(data):
    with open(SETTINGS_PATH, "w") as f:
        json.dump(data, f, indent=2)

@app.route("/api/settings", methods=["GET"])
def get_settings():
    s = load_settings()
    # Mask sensitive values
    masked = {}
    for k, v in s.items():
        if v and k in ("openai_key", "anthropic_key", "fellow_password"):
            masked[k] = v[:4] + "..." + v[-4:] if len(v) > 8 else "****"
        else:
            masked[k] = v
    masked["has_openai_key"] = bool(s.get("openai_key"))
    masked["has_anthropic_key"] = bool(s.get("anthropic_key"))
    masked["has_fellow_creds"] = bool(s.get("fellow_email") and s.get("fellow_password"))
    return jsonify(masked)

@app.route("/api/settings", methods=["POST"])
def post_settings():
    data = request.json or {}
    s = load_settings()
    # Only update fields that are provided (non-empty)
    for k in ("openai_key", "anthropic_key", "fellow_email", "fellow_password", "ai_provider"):
        if k in data and data[k] != "":
            s[k] = data[k]
    save_settings_file(s)
    return jsonify({"ok": True})


# ─── AI Parsing ───────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are an expert specialty coffee consultant with deep knowledge of coffee origins, processing methods, roast levels, and brewing science. You help dial in grind settings and brew profiles for the Fellow Ode Gen 1 grinder and Fellow Aiden brewer.

When given coffee bag text or a coffee name, extract and infer the following as JSON:
{
  "coffee_name": "short name for this coffee",
  "roaster": "roaster name if mentioned",
  "origin": "country or region",
  "process": "washed | natural | honey | anaerobic | wet-hulled | other",
  "roast": "light | medium-light | medium | medium-dark | dark",
  "altitude_m": number or null,
  "variety": "coffee variety if mentioned",
  "flavor_notes": ["array", "of", "tasting", "notes"],
  "roaster_temp_c": number or null (convert F to C if needed),
  "confidence": "high | medium | low",
  "reasoning": "1-2 sentence explanation of how you determined the roast level and key parameters"
}

Rules:
- If the text mentions specific flavor notes (jasmine, citrus, blueberry = light; chocolate, caramel = medium; smoky, earthy = dark), use those to infer roast if not stated
- Specialty coffee from Africa (Ethiopia, Kenya, Rwanda) defaults to light unless stated otherwise
- Bottomless subscriptions default to specialty/light-medium unless stated otherwise
- Natural process coffees are slightly more soluble than washed; account for this in your reasoning
- Be conservative — if uncertain between light and medium-light, say medium-light
- Always return valid JSON, nothing else"""

def call_ai(prompt, settings):
    provider = settings.get("ai_provider", "anthropic")

    if provider == "openai" and settings.get("openai_key"):
        return call_openai(prompt, settings["openai_key"])
    elif settings.get("anthropic_key"):
        return call_anthropic(prompt, settings["anthropic_key"])
    elif settings.get("openai_key"):
        return call_openai(prompt, settings["openai_key"])
    else:
        return None, "No AI API key configured. Add one in Settings."

def call_anthropic(prompt, api_key):
    try:
        import urllib.request
        payload = json.dumps({
            "model": "claude-haiku-4-5-20251001",
            "max_tokens": 1024,
            "system": SYSTEM_PROMPT,
            "messages": [{"role": "user", "content": prompt}]
        }).encode()

        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=payload,
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
            text = data["content"][0]["text"].strip()
            # Strip markdown code fences if present
            text = re.sub(r'^```json\s*', '', text)
            text = re.sub(r'\s*```$', '', text)
            return json.loads(text), None
    except Exception as e:
        return None, f"Anthropic API error: {str(e)}"

def call_openai(prompt, api_key):
    try:
        import urllib.request
        payload = json.dumps({
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            "response_format": {"type": "json_object"},
            "max_tokens": 1024,
        }).encode()

        req = urllib.request.Request(
            "https://api.openai.com/v1/chat/completions",
            data=payload,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
            text = data["choices"][0]["message"]["content"].strip()
            return json.loads(text), None
    except Exception as e:
        return None, f"OpenAI API error: {str(e)}"

@app.route("/api/parse-bag", methods=["POST"])
def parse_bag():
    data = request.json or {}
    bag_text = (data.get("bag_text") or "").strip()
    if not bag_text:
        return jsonify({"error": "bag_text required"}), 400

    settings = load_settings()
    result, err = call_ai(f"Parse this coffee bag description:\n\n{bag_text}", settings)
    if err:
        return jsonify({"error": err}), 500

    return jsonify(result)

@app.route("/api/search-coffee", methods=["POST"])
def search_coffee():
    data = request.json or {}
    query = (data.get("query") or "").strip()
    if not query:
        return jsonify({"error": "query required"}), 400

    settings = load_settings()
    prompt = f"""Search your knowledge for this coffee: "{query}"

If you recognize this coffee (or a close match), extract its details.
If you don't recognize it exactly, make reasonable inferences based on the roaster's known style, the origin, or the name.
Always return the JSON structure. Set confidence to "low" if guessing."""

    result, err = call_ai(prompt, settings)
    if err:
        return jsonify({"error": err}), 500

    return jsonify(result)


# ─── Recommendation Engine ────────────────────────────────────────────────────

# Ode Gen 1 base grind settings for batch brew (1–11 scale)
# Batch brew range: light ~3-5, medium ~5-7, dark ~7-9
ROAST_BASE = {
    "light":        {"grind": 4.0,  "temp_c": 96, "bloom_dur": 45, "bloom_ratio": 2.5, "ratio": 16.5, "pulses": 3, "pulse_int": 30},
    "medium-light": {"grind": 5.0,  "temp_c": 94, "bloom_dur": 40, "bloom_ratio": 2.5, "ratio": 16.0, "pulses": 3, "pulse_int": 28},
    "medium":       {"grind": 6.0,  "temp_c": 93, "bloom_dur": 35, "bloom_ratio": 2.0, "ratio": 15.5, "pulses": 2, "pulse_int": 25},
    "medium-dark":  {"grind": 7.0,  "temp_c": 91, "bloom_dur": 30, "bloom_ratio": 2.0, "ratio": 15.0, "pulses": 2, "pulse_int": 22},
    "dark":         {"grind": 8.0,  "temp_c": 89, "bloom_dur": 25, "bloom_ratio": 1.5, "ratio": 14.5, "pulses": 1, "pulse_int": 20},
}

ORIGIN_ADJUSTMENTS = {
    "ethiopia":  {"temp_bias": +1, "grind_bias": 0},
    "kenya":     {"temp_bias": +1, "grind_bias": 0},
    "rwanda":    {"temp_bias": 0,  "grind_bias": 0},
    "burundi":   {"temp_bias": 0,  "grind_bias": 0},
    "colombia":  {"temp_bias": 0,  "grind_bias": 0},
    "brazil":    {"temp_bias": -2, "grind_bias": +1},
    "guatemala": {"temp_bias": 0,  "grind_bias": 0},
    "sumatra":   {"temp_bias": -2, "grind_bias": +1},
    "indonesia": {"temp_bias": -2, "grind_bias": +1},
    "panama":    {"temp_bias": 0,  "grind_bias": 0},
    "costa rica":{"temp_bias": 0,  "grind_bias": 0},
    "honduras":  {"temp_bias": -1, "grind_bias": 0},
    "peru":      {"temp_bias": 0,  "grind_bias": 0},
}

PROCESS_ADJUSTMENTS = {
    "washed":    {"temp_bias": +1, "grind_bias": 0},
    "natural":   {"temp_bias": -1, "grind_bias": +0.5},
    "honey":     {"temp_bias": 0,  "grind_bias": +0.5},
    "anaerobic": {"temp_bias": -1, "grind_bias": +1},
    "wet-hulled":{"temp_bias": -1, "grind_bias": +1},
}

# Oz-based batch size → grind offset (larger batch = slightly coarser)
def batch_grind_offset(oz):
    if oz <= 10:   return -0.5
    if oz <= 16:   return 0
    if oz <= 22:   return +0.5
    return +1.0

def build_recommendation(coffee_data, oz, grams, history_rows):
    roast = coffee_data.get("roast", "medium")
    origin = (coffee_data.get("origin") or "").lower()
    process = (coffee_data.get("process") or "").lower()
    roaster_temp = coffee_data.get("roaster_temp_c")

    base = dict(ROAST_BASE.get(roast, ROAST_BASE["medium"]))

    grind_bias = 0.0
    temp_bias = 0.0
    bias_notes = []

    # Origin
    for key, adj in ORIGIN_ADJUSTMENTS.items():
        if key in origin:
            grind_bias += adj["grind_bias"]
            temp_bias  += adj["temp_bias"]
            if adj["temp_bias"] != 0 or adj["grind_bias"] != 0:
                bias_notes.append(f"{key.title()} origin adjustment applied")
            break

    # Process
    for key, adj in PROCESS_ADJUSTMENTS.items():
        if key in process:
            grind_bias += adj["grind_bias"]
            temp_bias  += adj["temp_bias"]
            if adj["temp_bias"] != 0 or adj["grind_bias"] != 0:
                bias_notes.append(f"{key} process adjustment applied")
            break

    # Batch size
    offset = batch_grind_offset(oz)
    grind_bias += offset
    if offset != 0:
        bias_notes.append(f"{oz}oz batch size adjustment")

    # Learning from history
    similar = [b for b in history_rows if b["roast"] == roast]
    if similar:
        bitter_count = sum(1 for b in similar if b["rating"] == "bitter")
        bright_count = sum(1 for b in similar if b["rating"] == "bright")
        flat_count   = sum(1 for b in similar if b["rating"] == "flat")
        if bitter_count > bright_count + flat_count:
            grind_bias += 0.5
            bias_notes.append(f"History: {bitter_count} bitter brews → adjusted coarser")
        elif bright_count + flat_count > bitter_count:
            grind_bias -= 0.5
            bias_notes.append(f"History: {bright_count + flat_count} bright/flat brews → adjusted finer")

    # Compute final values
    grind = max(1.0, min(11.0, round(base["grind"] + grind_bias, 1)))
    temp_c = roaster_temp or (base["temp_c"] + temp_bias)
    temp_c = round(temp_c, 1)

    return {
        "grind": grind,
        "temp_c": temp_c,
        "temp_f": round(temp_c * 9/5 + 32, 1),
        "bloom_dur": base["bloom_dur"],
        "bloom_ratio": base["bloom_ratio"],
        "ratio": base["ratio"],
        "pulses": base["pulses"],
        "pulse_int": base["pulse_int"],
        "bias_notes": bias_notes,
    }

@app.route("/api/recommend", methods=["POST"])
def recommend():
    data = request.json or {}
    coffee_data = data.get("coffee_data", {})
    oz    = float(data.get("oz", 12.5))
    grams = float(data.get("grams", 22.0))

    with get_db() as conn:
        rows = conn.execute("SELECT roast, rating FROM brews WHERE rating IS NOT NULL").fetchall()

    rec = build_recommendation(coffee_data, oz, grams, rows)
    return jsonify(rec)


# ─── Brew History ──────────────────────────────────────────────────────────────

@app.route("/api/history", methods=["GET"])
def get_history():
    limit = int(request.args.get("limit", 50))
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM brews ORDER BY timestamp DESC LIMIT ?", (limit,)
        ).fetchall()
    return jsonify([dict(r) for r in rows])

@app.route("/api/history", methods=["POST"])
def post_history():
    data = request.json or {}
    data["timestamp"] = data.get("timestamp", int(time.time() * 1000))
    fields = ["timestamp","bag_text","coffee_name","roast","origin","process","roaster",
              "grind","temp_c","ratio","bloom_dur","bloom_ratio","pulses","pulse_int",
              "brew_oz","brew_grams","preset_name","rating","notes","rationale"]
    vals = {f: data.get(f) for f in fields}
    cols = ", ".join(vals.keys())
    placeholders = ", ".join(["?"] * len(vals))
    with get_db() as conn:
        cur = conn.execute(f"INSERT INTO brews ({cols}) VALUES ({placeholders})", list(vals.values()))
        conn.commit()
        row = conn.execute("SELECT * FROM brews WHERE id = ?", (cur.lastrowid,)).fetchone()
    return jsonify(dict(row)), 201

@app.route("/api/history/<int:brew_id>", methods=["PUT"])
def put_history(brew_id):
    data = request.json or {}
    allowed = ["rating", "notes", "grind", "temp_c"]
    updates = {k: v for k, v in data.items() if k in allowed}
    if not updates:
        return jsonify({"error": "No valid fields to update"}), 400
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    with get_db() as conn:
        conn.execute(f"UPDATE brews SET {set_clause} WHERE id = ?", [*updates.values(), brew_id])
        conn.commit()
        row = conn.execute("SELECT * FROM brews WHERE id = ?", (brew_id,)).fetchone()
    return jsonify(dict(row))

@app.route("/api/history/<int:brew_id>", methods=["DELETE"])
def delete_history(brew_id):
    with get_db() as conn:
        conn.execute("DELETE FROM brews WHERE id = ?", (brew_id,))
        conn.commit()
    return jsonify({"ok": True})


# ─── Presets ───────────────────────────────────────────────────────────────────

@app.route("/api/presets", methods=["GET"])
def get_presets():
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM presets ORDER BY sort_order, id").fetchall()
    return jsonify([dict(r) for r in rows])

@app.route("/api/presets", methods=["POST"])
def post_preset():
    data = request.json or {}
    name  = data.get("name", "").strip()
    oz    = float(data.get("oz", 12.5))
    grams = float(data.get("grams", 22.0))
    if not name:
        return jsonify({"error": "name required"}), 400
    with get_db() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO presets (name, oz, grams) VALUES (?, ?, ?)",
            (name, oz, grams)
        )
        conn.commit()
        row = conn.execute("SELECT * FROM presets WHERE name = ?", (name,)).fetchone()
    return jsonify(dict(row)), 201

@app.route("/api/presets/<int:preset_id>", methods=["DELETE"])
def delete_preset(preset_id):
    with get_db() as conn:
        conn.execute("DELETE FROM presets WHERE id = ?", (preset_id,))
        conn.commit()
    return jsonify({"ok": True})


# ─── Aiden Push ────────────────────────────────────────────────────────────────

@app.route("/api/push-aiden", methods=["POST"])
def push_aiden():
    data = request.json or {}
    settings = load_settings()

    email    = settings.get("fellow_email")
    password = settings.get("fellow_password")
    if not email or not password:
        return jsonify({"error": "Fellow credentials not configured. Add them in Settings."}), 400

    profile_name = data.get("profile_name", "Coffee Dial Profile")
    rec = data.get("rec", {})

    try:
        from fellow_aiden import FellowAiden  # pip install fellow-aiden
        fa = FellowAiden(email, password)
        profile = {
            "title": profile_name,
            "ratio": rec.get("ratio", 16),
            "bloomEnabled": True,
            "bloomRatio": rec.get("bloom_ratio", 2.5),
            "bloomDuration": rec.get("bloom_dur", 40),
            "bloomTemperature": rec.get("temp_c", 94),
            "ssPulsesEnabled": rec.get("pulses", 1) > 1,
            "ssPulsesNumber": rec.get("pulses", 1),
            "ssPulsesInterval": rec.get("pulse_int", 25),
            "ssPulseTemperatures": [rec.get("temp_c", 94)] * rec.get("pulses", 1),
            "batchPulsesEnabled": False,
        }
        result = fa.create_profile(profile)
        return jsonify({"ok": True, "profile": result})
    except ImportError:
        return jsonify({
            "error": "fellow-aiden package not installed. Run: pip install fellow-aiden",
            "install_cmd": "pip install fellow-aiden"
        }), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8765))
    print(f"\n☕  Coffee Dial backend running at http://localhost:{port}\n")
    app.run(host="0.0.0.0", port=port, debug=True)
