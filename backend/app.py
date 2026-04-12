"""
Coffee Dial — Backend Server
Flask + SQLite backend for the Coffee Dial web app.

Endpoints:
  POST /api/parse-bag         — AI-powered bag text parsing
  POST /api/search-coffee     — Search for a coffee by name using AI
  POST /api/recommend         — Get grind + brew recommendation
  GET  /api/equipment         — List all available grinders and brewers
  GET  /api/user-equipment    — Get user's saved equipment
  POST /api/user-equipment    — Save user equipment selection
  GET  /api/history           — Fetch brew history
  POST /api/history           — Save a brew entry
  PUT  /api/history/<id>      — Update a brew entry (e.g. add rating)
  DELETE /api/history/<id>    — Delete a brew entry
  GET  /api/presets           — Get volume presets
  POST /api/presets           — Save a volume preset
  DELETE /api/presets/<id>    — Delete a preset
  POST /api/push-aiden        — Push a profile to Fellow Aiden
  GET  /api/settings          — Get settings (masked credentials)
  POST /api/settings          — Save settings
"""

import os
import json
import sqlite3
import time
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

from ai.parsing import call_ai
from ai.recipe_search import search_roaster_recipe
from engine.recommend import build_recommendation
from equipment.loader import get_grinder, get_brewer, list_equipment
from community.loader import search_recipes, scale_recipe
from community.brewlink import fetch_brewlink_profile, brewlink_to_community_recipe

FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")

app = Flask(__name__, static_folder=os.path.join(FRONTEND_DIR, "dist"))
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
                grinder_id  TEXT,
                brewer_id   TEXT,
                grind       REAL,
                grinder_setting_display TEXT,
                target_microns REAL,
                temp_c      REAL,
                ratio       REAL,
                dose_g      REAL,
                water_g     REAL,
                brew_oz     REAL,
                recipe_json TEXT,
                preset_name TEXT,
                rating      TEXT,
                notes       TEXT,
                rationale   TEXT
            );

            CREATE TABLE IF NOT EXISTS presets (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT NOT NULL UNIQUE,
                oz          REAL NOT NULL,
                sort_order  INTEGER DEFAULT 0
            );

            INSERT OR IGNORE INTO presets (name, oz, sort_order) VALUES
                ('Solo (12oz)',     12.0, 0),
                ('Two cups (20oz)', 20.0, 1),
                ('Full pot (32oz)', 32.0, 2);

            CREATE TABLE IF NOT EXISTS user_equipment (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                equipment_type TEXT NOT NULL,
                equipment_id   TEXT NOT NULL,
                is_default     INTEGER DEFAULT 0,
                added_at       INTEGER NOT NULL,
                UNIQUE(equipment_type, equipment_id)
            );
        """)

        # Migrate legacy schemas from pre-multi-equipment versions
        _migrate_brews(conn)
        _migrate_presets(conn)


def _get_columns(conn, table):
    """Return set of column names for a table."""
    cursor = conn.execute(f"PRAGMA table_info({table})")
    return {row[1] for row in cursor.fetchall()}


def _migrate_brews(conn):
    """Add new columns to brews table if upgrading from old schema."""
    cols = _get_columns(conn, "brews")
    new_columns = {
        "grinder_id": "TEXT",
        "brewer_id": "TEXT",
        "grinder_setting_display": "TEXT",
        "target_microns": "REAL",
        "dose_g": "REAL",
        "water_g": "REAL",
        "recipe_json": "TEXT",
    }
    for col, col_type in new_columns.items():
        if col not in cols:
            conn.execute(f"ALTER TABLE brews ADD COLUMN {col} {col_type}")


def _migrate_presets(conn):
    """Handle legacy presets table that had a NOT NULL grams column."""
    cols = _get_columns(conn, "presets")
    if "grams" in cols:
        # SQLite can't drop columns in older versions, so recreate the table
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS presets_new (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT NOT NULL UNIQUE,
                oz          REAL NOT NULL,
                sort_order  INTEGER DEFAULT 0
            );
            INSERT OR IGNORE INTO presets_new (id, name, oz, sort_order)
                SELECT id, name, oz, sort_order FROM presets;
            DROP TABLE presets;
            ALTER TABLE presets_new RENAME TO presets;
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
    masked = {}
    for k, v in s.items():
        if v and k in ("openai_key", "anthropic_key", "fellow_password"):
            masked[k] = v[:4] + "..." + v[-4:] if len(v) > 8 else "****"
        else:
            masked[k] = v
    masked["has_openai_key"] = bool(s.get("openai_key"))
    masked["has_anthropic_key"] = bool(s.get("anthropic_key"))
    masked["has_fellow_creds"] = bool(s.get("fellow_email") and s.get("fellow_password"))
    masked.setdefault("temp_unit", "F")
    return jsonify(masked)

@app.route("/api/settings", methods=["POST"])
def post_settings():
    data = request.json or {}
    s = load_settings()
    for k in ("openai_key", "anthropic_key", "fellow_email", "fellow_password", "ai_provider", "temp_unit"):
        if k in data and data[k] != "":
            s[k] = data[k]
    save_settings_file(s)
    return jsonify({"ok": True})


# ─── Equipment ────────────────────────────────────────────────────────────────

@app.route("/api/equipment", methods=["GET"])
def get_equipment():
    return jsonify(list_equipment())

@app.route("/api/user-equipment", methods=["GET"])
def get_user_equipment():
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM user_equipment ORDER BY equipment_type, is_default DESC"
        ).fetchall()
    return jsonify([dict(r) for r in rows])

@app.route("/api/user-equipment", methods=["POST"])
def post_user_equipment():
    data = request.json or {}
    eq_type = data.get("equipment_type", "").strip()
    eq_id = data.get("equipment_id", "").strip()
    is_default = int(data.get("is_default", 0))

    if not eq_type or not eq_id:
        return jsonify({"error": "equipment_type and equipment_id required"}), 400

    with get_db() as conn:
        if is_default:
            conn.execute(
                "UPDATE user_equipment SET is_default = 0 WHERE equipment_type = ?",
                (eq_type,)
            )
        conn.execute(
            """INSERT INTO user_equipment (equipment_type, equipment_id, is_default, added_at)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(equipment_type, equipment_id) DO UPDATE SET is_default = excluded.is_default""",
            (eq_type, eq_id, is_default, int(time.time() * 1000))
        )
        conn.commit()
        rows = conn.execute(
            "SELECT * FROM user_equipment WHERE equipment_type = ? ORDER BY is_default DESC",
            (eq_type,)
        ).fetchall()
    return jsonify([dict(r) for r in rows]), 201

@app.route("/api/user-equipment/<int:eq_id>", methods=["DELETE"])
def delete_user_equipment(eq_id):
    with get_db() as conn:
        conn.execute("DELETE FROM user_equipment WHERE id = ?", (eq_id,))
        conn.commit()
    return jsonify({"ok": True})


# ─── AI Parsing ───────────────────────────────────────────────────────────────

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


# ─── Recommendation ──────────────────────────────────────────────────────────

@app.route("/api/recommend", methods=["POST"])
def recommend():
    data = request.json or {}
    coffee_data = data.get("coffee_data", {})
    grinder_id = data.get("grinder_id", "fellow_ode_gen1")
    brewer_id = data.get("brewer_id", "fellow_aiden")
    oz = float(data.get("oz", 12))

    grinder = get_grinder(grinder_id)
    brewer = get_brewer(brewer_id)

    if not grinder:
        return jsonify({"error": f"Unknown grinder: {grinder_id}"}), 400
    if not brewer:
        return jsonify({"error": f"Unknown brewer: {brewer_id}"}), 400

    with get_db() as conn:
        rows = conn.execute("SELECT roast, rating FROM brews WHERE rating IS NOT NULL").fetchall()

    rec = build_recommendation(coffee_data, grinder, brewer, oz, rows)
    return jsonify(rec)


# ─── Brew History ─────────────────────────────────────────────────────────────

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
    fields = ["timestamp", "bag_text", "coffee_name", "roast", "origin", "process", "roaster",
              "grinder_id", "brewer_id", "grind", "grinder_setting_display", "target_microns",
              "temp_c", "ratio", "dose_g", "water_g", "brew_oz",
              "recipe_json", "preset_name", "rating", "notes", "rationale"]
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


# ─── Presets ──────────────────────────────────────────────────────────────────

@app.route("/api/presets", methods=["GET"])
def get_presets():
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM presets ORDER BY sort_order, id").fetchall()
    return jsonify([dict(r) for r in rows])

@app.route("/api/presets", methods=["POST"])
def post_preset():
    data = request.json or {}
    name = data.get("name", "").strip()
    oz = float(data.get("oz", 12))
    if not name:
        return jsonify({"error": "name required"}), 400
    with get_db() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO presets (name, oz) VALUES (?, ?)",
            (name, oz)
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


# ─── Aiden Push ───────────────────────────────────────────────────────────────

@app.route("/api/push-aiden", methods=["POST"])
def push_aiden():
    data = request.json or {}
    settings = load_settings()

    email = settings.get("fellow_email")
    password = settings.get("fellow_password")
    if not email or not password:
        return jsonify({"error": "Fellow credentials not configured. Add them in Settings."}), 400

    profile_name = data.get("profile_name", "Coffee Dial Profile")
    rec = data.get("rec", {})

    try:
        from fellow_aiden import FellowAiden

        # Monkey-patch: fellow-aiden 0.2.2 crashes if device response
        # lacks 'profiles' or 'schedules' keys (API schema change).
        _orig_device = FellowAiden._FellowAiden__device
        def _safe_device(self):
            import json as _json
            self._log.debug("Fetching device for account")
            device_url = self.BASE_URL + self.API_DEVICES
            response = self.SESSION.get(device_url, params={'dataType': 'real'})
            if response.status_code == 401:
                self._FellowAiden__auth()
                response = self.SESSION.get(device_url, params={'dataType': 'real'})
            parsed = _json.loads(response.content)
            self._device_config = parsed[0]
            self._brewer_id = self._device_config['id']
            self._profiles = self._device_config.get('profiles', [])
            self._schedules = self._device_config.get('schedules', [])
            self._log.debug("Brewer ID: %s" % self._brewer_id)
            self._log.info("Device and profile information set")
        FellowAiden._FellowAiden__device = _safe_device

        fa = FellowAiden(email, password)

        # Normalize field names: accept both engine snake_case and Fellow camelCase
        def _get(engine_key, fellow_key, default):
            return rec.get(engine_key, rec.get(fellow_key, default))

        # Snap ratio to Aiden's allowed values (14–20 in 0.5 steps)
        raw_ratio = _get("ratio", "ratio", 16)
        ratio = round(raw_ratio * 2) / 2  # nearest 0.5
        ratio = max(14.0, min(20.0, ratio))

        # Snap bloom ratio (1–3 in 0.5 steps)
        raw_bloom = _get("bloom_ratio", "bloomRatio", 2.5)
        bloom_ratio = round(raw_bloom * 2) / 2
        bloom_ratio = max(1.0, min(3.0, bloom_ratio))

        # Temps must be Celsius, snapped to 0.5, range 50–99
        raw_temp = _get("temp_c", "bloomTemperature", 94)
        temp_c = round(raw_temp * 2) / 2
        temp_c = max(50.0, min(99.0, temp_c))

        pulses = max(1, min(10, _get("pulses", "ssPulsesNumber", 1)))
        bloom_dur = max(1, min(120, _get("bloom_dur", "bloomDuration", 40)))
        pulse_int = max(5, min(60, _get("pulse_int", "ssPulsesInterval", 25)))

        profile = {
            "profileType": 0,
            "title": profile_name[:50],
            "ratio": ratio,
            "bloomEnabled": True,
            "bloomRatio": bloom_ratio,
            "bloomDuration": bloom_dur,
            "bloomTemperature": temp_c,
            "ssPulsesEnabled": pulses > 1,
            "ssPulsesNumber": pulses,
            "ssPulsesInterval": pulse_int,
            "ssPulseTemperatures": [temp_c] * pulses,
            "batchPulsesEnabled": False,
            "batchPulsesNumber": 1,
            "batchPulsesInterval": 5,
            "batchPulseTemperatures": [temp_c],
        }
        result = fa.create_profile(profile)
        return jsonify({"ok": True, "profile": result})
    except ImportError:
        return jsonify({
            "error": "fellow-aiden package not installed. Run: pip install fellow-aiden",
            "install_cmd": "pip install fellow-aiden"
        }), 500
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# ─── Community Recipes ───────────────────────────────────────────────────────────

@app.route("/api/community-recipes", methods=["GET"])
def get_community_recipes_api():
    brewer_id = request.args.get("brewer_id")
    brew_method = request.args.get("brew_method")
    oz = request.args.get("oz", type=float)

    recipes = search_recipes(brewer_id=brewer_id, brew_method=brew_method)

    if oz:
        water_g = oz * 29.5735
        recipes = [scale_recipe(r, water_g) for r in recipes]

    return jsonify(recipes)


@app.route("/api/search-roaster-recipe", methods=["POST"])
def search_roaster_recipe_api():
    data = request.json or {}
    roaster = (data.get("roaster") or "").strip()
    coffee_name = (data.get("coffee_name") or "").strip()
    brew_method = (data.get("brew_method") or "").strip()
    brewer_name = (data.get("brewer_name") or "").strip()

    if not roaster:
        return jsonify({"error": "roaster name required"}), 400

    settings = load_settings()
    result, err = search_roaster_recipe(roaster, coffee_name, brew_method, brewer_name, settings)
    if err:
        return jsonify({"error": err}), 500

    return jsonify(result)


@app.route("/api/import-brew-link", methods=["POST"])
def import_brew_link():
    data = request.json or {}
    link = (data.get("link") or "").strip()
    if not link:
        return jsonify({"error": "link required"}), 400

    settings = load_settings()
    profile, err = fetch_brewlink_profile(link, settings)
    if err:
        return jsonify({"error": err}), 500

    recipe = brewlink_to_community_recipe(profile)
    return jsonify(recipe)


# ─── Frontend ───────────────────────────────────────────────────────────────────

@app.route("/")
def serve_frontend():
    return send_from_directory(os.path.join(FRONTEND_DIR, "dist"), "index.html")


@app.route("/<path:path>")
def serve_static(path):
    return send_from_directory(os.path.join(FRONTEND_DIR, "dist"), path)


# ─── Main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8765))
    print(f"\n☕  Coffee Dial running at http://localhost:{port}\n")
    app.run(host="0.0.0.0", port=port, debug=True)
