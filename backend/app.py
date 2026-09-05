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
  GET  /api/bags              — List bags with computed freshness and last brew
  POST /api/bags              — Create a bag
  PUT  /api/bags/<id>         — Update a bag (roast date, open, freeze, thaw)
  POST /api/bags/<id>/rebuy   — Finish a bag and start a fresh one of the same coffee
  DELETE /api/bags/<id>       — Delete a bag
  POST /api/brews/<id>/rate   — Rate a brew, get the one change for the next
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
from engine.recommend import build_recommendation, lever_headroom
from engine import freshness
from engine import dialin
from equipment.loader import get_grinder, get_brewer, list_equipment
from community.loader import search_recipes, scale_recipe
from community.brewlink import fetch_brewlink_profile, brewlink_to_community_recipe
from aiden import AidenClient, AidenError, AidenAuthError

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

            CREATE TABLE IF NOT EXISTS bags (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                coffee_name TEXT NOT NULL,
                roaster     TEXT,
                roast       TEXT,
                origin      TEXT,
                process     TEXT,
                is_decaf    INTEGER DEFAULT 0,
                storage     TEXT DEFAULT 'vacuum',
                roast_date  INTEGER,
                opened_at   INTEGER,
                frozen_at   INTEGER,
                thawed_at   INTEGER,
                finished_at INTEGER,
                notes       TEXT,
                created_at  INTEGER NOT NULL
            );

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
        # Freshness: which bag this brew came from. Nullable, so brews logged
        # without a bag keep working exactly as before.
        "bag_id": "INTEGER",
        # Freshness as it was when the brew was made. Snapshotted so the
        # question "were my bitter cups from tired bags?" is one query, and
        # survives the bag being rebought or its freeze cleared later.
        "bag_phase": "TEXT",
        "bag_age_days": "REAL",
        "bag_open_age_days": "REAL",
        "bag_storage": "TEXT",
        # One-lever dial-in chain.
        "parent_brew_id": "INTEGER",
        "version": "INTEGER",
        "chain_micron_delta": "REAL",
        "chain_temp_delta_c": "REAL",
        "chain_ratio_delta": "REAL",
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

    # An explicit chain wins; otherwise the parent brew's chain plus the one
    # move its rating calls for, so a follow-up continues the same dial-in.
    chain = data.get("chain")
    parent_brew_id = data.get("parent_brew_id")
    version = data.get("version") or 1
    adjustment = None

    with get_db() as conn:
        rows = conn.execute("SELECT roast, rating FROM brews WHERE rating IS NOT NULL").fetchall()
        if chain is None and parent_brew_id:
            try:
                chain, version, adjustment, _ = _chain_for_child(conn, parent_brew_id)
            except LookupError as e:
                return jsonify({"error": str(e)}), 404

    rec = build_recommendation(coffee_data, grinder, brewer, oz, rows, chain=chain)
    rec["version"] = version
    rec["parent_brew_id"] = parent_brew_id if chain is not None else None
    if adjustment is not None:
        rec["adjustment"] = adjustment
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

BREW_FIELDS = ["timestamp", "bag_text", "coffee_name", "roast", "origin", "process", "roaster",
               "grinder_id", "brewer_id", "grind", "grinder_setting_display", "target_microns",
               "temp_c", "ratio", "dose_g", "water_g", "brew_oz",
               "recipe_json", "preset_name", "rating", "notes", "rationale",
               "bag_id", "bag_phase", "bag_age_days", "bag_open_age_days", "bag_storage",
               "parent_brew_id", "version",
               "chain_micron_delta", "chain_temp_delta_c", "chain_ratio_delta"]

CHAIN_COLUMNS = {
    "chain_micron_delta": "micron_delta",
    "chain_temp_delta_c": "temp_delta_c",
    "chain_ratio_delta": "ratio_delta",
}


@app.route("/api/history", methods=["POST"])
def post_history():
    data = request.json or {}
    data["timestamp"] = data.get("timestamp", int(time.time() * 1000))
    vals = {f: data.get(f) for f in BREW_FIELDS}

    with get_db() as conn:
        # A child brew inherits its chain and version from the parent unless
        # the caller spelled them out. Server-side, so the frontend only has
        # to carry one id.
        parent_brew_id = data.get("parent_brew_id")
        if parent_brew_id and not any(data.get(c) is not None for c in CHAIN_COLUMNS):
            try:
                chain, version, _, _ = _chain_for_child(conn, parent_brew_id)
            except LookupError as e:
                return jsonify({"error": str(e)}), 400
            for col, key in CHAIN_COLUMNS.items():
                vals[col] = chain[key]
            if vals["version"] is None:
                vals["version"] = version
        if vals["version"] is None:
            vals["version"] = 1

        # Snapshot the bag's freshness at brew time.
        if vals["bag_id"]:
            bag = conn.execute("SELECT * FROM bags WHERE id = ?", (vals["bag_id"],)).fetchone()
            if bag is None:
                return jsonify({"error": f"Bag {vals['bag_id']} not found"}), 400
            read = freshness.compute_phase(dict(bag), vals["timestamp"] // 1000)
            vals["bag_phase"] = read["phase"]
            vals["bag_age_days"] = read.get("age_days")
            vals["bag_open_age_days"] = read.get("open_age_days")
            vals["bag_storage"] = bag["storage"]

        cols = ", ".join(vals.keys())
        placeholders = ", ".join(["?"] * len(vals))
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

@app.route("/api/history", methods=["DELETE"])
def delete_all_history():
    with get_db() as conn:
        result = conn.execute("DELETE FROM brews")
        conn.commit()
    return jsonify({"ok": True, "deleted": result.rowcount})


# ─── Bags & Freshness ─────────────────────────────────────────────────────────

BAG_FIELDS = ["coffee_name", "roaster", "roast", "origin", "process", "is_decaf",
              "storage", "roast_date", "opened_at", "frozen_at", "thawed_at",
              "finished_at", "notes"]


def _bag_with_freshness(row, now=None):
    """Attach the computed freshness read to a bag row."""
    bag = dict(row)
    now = now if now is not None else int(time.time())
    bag["freshness"] = freshness.compute_phase(bag, now)
    return bag


def _attach_brews(conn, bag):
    """How many brews came from this bag, and the latest one — the dial-in
    chain's natural parent for the next brew."""
    bag["brew_count"] = conn.execute(
        "SELECT COUNT(*) FROM brews WHERE bag_id = ?", (bag["id"],)
    ).fetchone()[0]
    last = conn.execute(
        "SELECT id, timestamp, version, rating, bag_phase FROM brews "
        "WHERE bag_id = ? ORDER BY timestamp DESC, id DESC LIMIT 1", (bag["id"],)
    ).fetchone()
    if last is None:
        bag["last_brew"] = None
    else:
        ratings = dialin.normalize_ratings(last["rating"])
        bag["last_brew"] = {
            "id": last["id"],
            "timestamp": last["timestamp"],
            "version": last["version"] or 1,
            "rating": last["rating"],
            "bag_phase": last["bag_phase"],
            "chain_complete": "good" in ratings,
        }
    return bag


@app.route("/api/bags", methods=["GET"])
def get_bags():
    include_finished = request.args.get("include_finished") == "1"
    query = "SELECT * FROM bags"
    if not include_finished:
        query += " WHERE finished_at IS NULL"
    query += " ORDER BY created_at DESC"
    with get_db() as conn:
        rows = conn.execute(query).fetchall()
        bags = [_attach_brews(conn, _bag_with_freshness(r)) for r in rows]
    return jsonify(bags)


@app.route("/api/bags", methods=["POST"])
def post_bag():
    data = request.json or {}
    name = (data.get("coffee_name") or "").strip()
    if not name:
        return jsonify({"error": "coffee_name required"}), 400

    vals = {f: data.get(f) for f in BAG_FIELDS}
    vals["coffee_name"] = name
    vals["is_decaf"] = 1 if data.get("is_decaf") else 0
    vals["storage"] = data.get("storage") or freshness.DEFAULT_STORAGE
    vals["created_at"] = int(time.time())

    cols = ", ".join(vals.keys())
    placeholders = ", ".join(["?"] * len(vals))
    with get_db() as conn:
        cur = conn.execute(
            f"INSERT INTO bags ({cols}) VALUES ({placeholders})", list(vals.values())
        )
        conn.commit()
        row = conn.execute("SELECT * FROM bags WHERE id = ?", (cur.lastrowid,)).fetchone()
    return jsonify(_bag_with_freshness(row)), 201


@app.route("/api/bags/<int:bag_id>", methods=["PUT"])
def put_bag(bag_id):
    data = request.json or {}
    updates = {k: v for k, v in data.items() if k in BAG_FIELDS}
    if not updates:
        return jsonify({"error": "No valid fields to update"}), 400
    if "is_decaf" in updates:
        updates["is_decaf"] = 1 if updates["is_decaf"] else 0

    set_clause = ", ".join(f"{k} = ?" for k in updates)
    with get_db() as conn:
        conn.execute(f"UPDATE bags SET {set_clause} WHERE id = ?", [*updates.values(), bag_id])
        conn.commit()
        row = conn.execute("SELECT * FROM bags WHERE id = ?", (bag_id,)).fetchone()
    if row is None:
        return jsonify({"error": "Bag not found"}), 404
    return jsonify(_bag_with_freshness(row))


@app.route("/api/bags/<int:bag_id>", methods=["DELETE"])
def delete_bag(bag_id):
    with get_db() as conn:
        conn.execute("DELETE FROM bags WHERE id = ?", (bag_id,))
        conn.commit()
    return jsonify({"ok": True})


@app.route("/api/bags/<int:bag_id>/rebuy", methods=["POST"])
def rebuy_bag(bag_id):
    """Finish this bag and start a new row for the same coffee.

    A new row rather than a reset of the old one: brews point at a bag by id,
    and their freshness snapshots only stay meaningful if the bag they point
    at keeps its roast date.
    """
    data = request.json or {}
    now = int(time.time())
    with get_db() as conn:
        old = conn.execute("SELECT * FROM bags WHERE id = ?", (bag_id,)).fetchone()
        if old is None:
            return jsonify({"error": "Bag not found"}), 404
        if old["finished_at"] is None:
            conn.execute("UPDATE bags SET finished_at = ? WHERE id = ?", (now, bag_id))

        vals = {f: old[f] for f in ("coffee_name", "roaster", "roast", "origin",
                                    "process", "is_decaf", "notes")}
        vals["storage"] = data.get("storage") or old["storage"] or freshness.DEFAULT_STORAGE
        vals["roast_date"] = data.get("roast_date")
        vals["created_at"] = now
        cols = ", ".join(vals.keys())
        placeholders = ", ".join(["?"] * len(vals))
        cur = conn.execute(
            f"INSERT INTO bags ({cols}) VALUES ({placeholders})", list(vals.values())
        )
        conn.commit()
        row = conn.execute("SELECT * FROM bags WHERE id = ?", (cur.lastrowid,)).fetchone()
        bag = _attach_brews(conn, _bag_with_freshness(row))
    return jsonify(bag), 201


# ─── Dial-in ──────────────────────────────────────────────────────────────────

@app.route("/api/brews/<int:brew_id>/rate", methods=["POST"])
def rate_brew(brew_id):
    """Record a rating and return the single change for the next brew.

    Does not create the next brew row — that happens when the next brew is
    logged with parent_brew_id set to this one.
    """
    data = request.json or {}
    ratings = data.get("ratings") or data.get("rating")
    if not ratings:
        return jsonify({"error": "rating required"}), 400

    rating_list = dialin.normalize_ratings(ratings)
    stored_rating = rating_list[0] if len(rating_list) == 1 else ",".join(rating_list)

    with get_db() as conn:
        brew = conn.execute("SELECT * FROM brews WHERE id = ?", (brew_id,)).fetchone()
        if brew is None:
            return jsonify({"error": "Brew not found"}), 404
        conn.execute("UPDATE brews SET rating = ? WHERE id = ?", (stored_rating, brew_id))
        conn.commit()
        brew = conn.execute("SELECT * FROM brews WHERE id = ?", (brew_id,)).fetchone()

    next_chain, next_version, adjustment = dialin.chain_for_child(brew, _headroom_for_brew(brew))

    response = {
        "brew_id": brew_id,
        "adjustment": adjustment,
        "next_chain": next_chain,
        "next_version": next_version,
        "chain_complete": adjustment["chain_complete"],
    }

    # When something actually moved, show what the next brew would look like.
    if adjustment["lever"]:
        grinder = get_grinder(brew["grinder_id"] or "")
        brewer = get_brewer(brew["brewer_id"] or "")
        if grinder and brewer:
            response["next_recommendation"] = build_recommendation(
                _coffee_from_brew(brew), grinder, brewer, brew["brew_oz"] or 12, [],
                chain=next_chain,
            )

    return jsonify(response)


def _coffee_from_brew(brew):
    return {
        "roast": brew["roast"],
        "origin": brew["origin"],
        "process": brew["process"],
        "coffee_name": brew["coffee_name"],
    }


def _headroom_for_brew(brew):
    """Which dial-in moves the brew's own brewer still has room for."""
    brewer = get_brewer(brew["brewer_id"] or "")
    if brewer is None:
        return None
    return lever_headroom(
        _coffee_from_brew(brew), brewer, brew["brew_oz"] or 12, dialin.chain_from_row(brew)
    )


def _chain_for_child(conn, parent_brew_id):
    """Chain, version and adjustment for the brew that follows `parent_brew_id`.

    Raises LookupError when the parent does not exist — a wrong id should be
    loud, not a silent restart from v1.
    """
    parent = conn.execute("SELECT * FROM brews WHERE id = ?", (parent_brew_id,)).fetchone()
    if parent is None:
        raise LookupError(f"Parent brew {parent_brew_id} not found")
    chain, version, adjustment = dialin.chain_for_child(parent, _headroom_for_brew(parent))
    return chain, version, adjustment, parent


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


# ─── Aiden ────────────────────────────────────────────────────────────────────

def _aiden_client():
    """Authenticate against the Fellow account. Returns (client, error_response)."""
    settings = load_settings()
    email = settings.get("fellow_email")
    password = settings.get("fellow_password")
    if not email or not password:
        return None, (jsonify({
            "error": "Fellow credentials not configured. Add them in Settings."
        }), 400)

    try:
        return AidenClient(email, password), None
    except AidenAuthError as e:
        return None, (jsonify({"error": str(e)}), 401)
    except AidenError as e:
        return None, (jsonify({"error": f"Could not reach the brewer: {e}"}), 502)


def _shape_profile(p):
    """Flatten one Fellow profile into what the UI needs.

    Fellow uses -1 and null interchangeably for "never used", so both become
    None here rather than surfacing as a 1969 timestamp.
    """
    last_used = p.get("lastUsedTime")
    if not isinstance(last_used, int) or last_used <= 0:
        last_used = None

    # Folder casing is inconsistent in Fellow's data ('drops' and 'Drops').
    folder = (p.get("folder") or "").strip()
    folder = folder.title() if folder else "Uncategorized"

    pulses = p.get("ssPulsesNumber") or 1

    # Fellow leaves overallTemperature null on plenty of profiles even though
    # the per-pulse temperatures are set. Fall back to those rather than
    # showing a blank, and say when the number was derived.
    temp_c = p.get("overallTemperature")
    temp_derived = False
    if temp_c is None:
        pulse_temps = [t for t in (p.get("ssPulseTemperatures") or []) if t is not None]
        if pulse_temps:
            temp_c = max(set(pulse_temps), key=pulse_temps.count)
            temp_derived = True
        elif p.get("bloomTemperature") is not None:
            temp_c = p.get("bloomTemperature")
            temp_derived = True

    return {
        "id": p.get("id"),
        "title": p.get("title") or "(untitled)",
        "folder": folder,
        "is_cold_brew": p.get("profileType") == 1,
        "is_default": bool(p.get("isDefaultProfile")),

        "last_used": last_used,
        "updated_at": p.get("updatedAt"),
        # Fellow's curated drops carry the date they landed on the brewer.
        "added_at": p.get("scheduledAt"),

        "ratio": p.get("ratio"),
        "temp_c": temp_c,
        "temp_is_derived": temp_derived,
        "bloom_enabled": bool(p.get("bloomEnabled")),
        "bloom_ratio": p.get("bloomRatio"),
        "bloom_duration_s": p.get("bloomDuration"),
        "bloom_temp_c": p.get("bloomTemperature"),
        "pulses": pulses,
        "pulse_interval_s": p.get("ssPulsesInterval"),
        "pulse_temps_c": p.get("ssPulseTemperatures") or [],
    }


@app.route("/api/aiden-profiles", methods=["GET"])
def get_aiden_profiles():
    """List the brew profiles currently on the brewer. Read-only."""
    client, err = _aiden_client()
    if err:
        return err

    try:
        raw = client.get_profiles()
        device = client.device()
    except AidenError as e:
        return jsonify({"error": str(e)}), 502

    profiles = [_shape_profile(p) for p in raw]
    # Most recently used first; never-used fall to the back, alphabetical.
    profiles.sort(key=lambda p: (p["last_used"] is None,
                                 -(p["last_used"] or 0),
                                 p["title"].lower()))

    return jsonify({
        "brewer": client.display_name,
        "count": len(profiles),
        "profiles": profiles,
        # Fellow exposes no per-profile brew counter. This is device-wide,
        # and is the only usage total available anywhere in the API.
        "device_totals": {
            "total_brewing_cycles": device.get("totalBrewingCycles"),
            "total_water_litres": device.get("totalWaterVolumeL"),
        },
    })


# ─── Aiden Push ───────────────────────────────────────────────────────────────

@app.route("/api/push-aiden", methods=["POST"])
def push_aiden():
    data = request.json or {}
    profile_name = data.get("profile_name", "Coffee Dial Profile")
    rec = data.get("rec", {})

    client, err = _aiden_client()
    if err:
        return err

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
    bloom_dur = max(1, min(120, _get("bloom_time_s", "bloomDuration", 40)))
    pulse_int = max(5, min(60, _get("pulse_interval_s", "ssPulsesInterval", 25)))

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

    try:
        result = client.create_profile(profile)
        return jsonify({"ok": True, "profile": result})
    except AidenError as e:
        return jsonify({"error": str(e)}), 502


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
