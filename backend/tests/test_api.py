"""Route-level tests against a scratch database. No AI, no brewer."""

import atexit
import os
import sys
import tempfile
import time

_DB = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_DB.close()
os.environ["COFFEE_DIAL_DB"] = _DB.name
atexit.register(lambda: os.path.exists(_DB.name) and os.unlink(_DB.name))

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest  # noqa: E402

import app as coffee_app  # noqa: E402
from engine import freshness  # noqa: E402

DAY = freshness.SECONDS_PER_DAY
COFFEE = {"coffee_name": "Probe", "roast": "light", "origin": "Ethiopia", "process": "washed"}
EQUIP = {"grinder_id": "fellow_ode_gen2", "brewer_id": "fellow_aiden", "brew_oz": 12}


@pytest.fixture
def client():
    with coffee_app.get_db() as conn:
        conn.execute("DELETE FROM brews")
        conn.execute("DELETE FROM bags")
        conn.commit()
    return coffee_app.app.test_client()


def recommend(client, **extra):
    body = {"coffee_data": COFFEE, "grinder_id": EQUIP["grinder_id"],
            "brewer_id": EQUIP["brewer_id"], "oz": 12, **extra}
    r = client.post("/api/recommend", json=body)
    assert r.status_code == 200, r.get_json()
    return r.get_json()


def log_brew(client, **extra):
    r = client.post("/api/history", json={**COFFEE, **EQUIP, **extra})
    assert r.status_code == 201, r.get_json()
    return r.get_json()


# ─── Dial-in chain across brews ───────────────────────────────────────────────

def test_child_recommendation_applies_the_parents_rating(client):
    """The old inherit path read the parent's own chain and dropped its rating."""
    base = recommend(client)
    v1 = log_brew(client)
    client.post(f"/api/brews/{v1['id']}/rate", json={"rating": "bright"})

    v2 = recommend(client, parent_brew_id=v1["id"])
    assert v2["version"] == 2
    assert v2["recipe"]["temp_c"] == base["recipe"]["temp_c"] + 2
    assert v2["target_microns"] == base["target_microns"]
    assert v2["chain"]["temp_delta_c"] == 2.0
    assert v2["adjustment"]["lever"] == "temp"


def test_logging_a_child_brew_derives_its_chain_and_version(client):
    v1 = log_brew(client)
    client.post(f"/api/brews/{v1['id']}/rate", json={"rating": "bitter"})
    v2 = log_brew(client, parent_brew_id=v1["id"])
    assert v2["version"] == 2
    assert v2["chain_micron_delta"] == 30.0
    assert v2["chain_temp_delta_c"] == 0.0

    client.post(f"/api/brews/{v2['id']}/rate", json={"rating": "flat"})
    v3 = log_brew(client, parent_brew_id=v2["id"])
    assert v3["version"] == 3
    assert v3["chain_micron_delta"] == 30.0
    assert v3["chain_ratio_delta"] == -0.5


def test_unknown_parent_is_a_loud_error(client):
    r = client.post("/api/recommend", json={"coffee_data": COFFEE, "oz": 12, "parent_brew_id": 9999})
    assert r.status_code == 404
    r = client.post("/api/history", json={**COFFEE, "parent_brew_id": 9999})
    assert r.status_code == 400


def test_brew_without_parent_is_version_one(client):
    assert log_brew(client)["version"] == 1


def test_rate_returns_next_recommendation_and_records_two_ratings(client):
    v1 = log_brew(client)
    r = client.post(f"/api/brews/{v1['id']}/rate", json={"ratings": ["bitter", "flat"]}).get_json()
    assert r["adjustment"]["lever"] == "grind"
    assert r["next_version"] == 2
    assert r["next_recommendation"]["target_microns"] > 0
    assert client.get("/api/history").get_json()[0]["rating"] == "bitter,flat"


# ─── Bags and brews ───────────────────────────────────────────────────────────

def make_bag(client, **overrides):
    body = {"coffee_name": "Probe", "roast": "light", "process": "washed",
            "storage": "vacuum", **overrides}
    r = client.post("/api/bags", json=body)
    assert r.status_code == 201, r.get_json()
    return r.get_json()


def test_bag_without_roast_date_reports_awaiting_and_no_numbers(client):
    bag = make_bag(client)
    assert bag["freshness"]["phase"] == "awaiting_roast_date"
    assert "ready_range_days" not in bag["freshness"]


def test_brew_snapshots_the_bags_freshness(client):
    now = int(time.time())
    bag = make_bag(client, roast_date=now - 14 * DAY, opened_at=now - 3 * DAY)
    brew = log_brew(client, bag_id=bag["id"])
    assert brew["bag_phase"] == "ready"
    assert 13.9 <= brew["bag_age_days"] <= 14.1
    assert 2.9 <= brew["bag_open_age_days"] <= 3.1
    assert brew["bag_storage"] == "vacuum"


def test_brew_from_unknown_bag_is_rejected(client):
    r = client.post("/api/history", json={**COFFEE, "bag_id": 9999})
    assert r.status_code == 400


def test_bag_list_carries_its_last_brew(client):
    bag = make_bag(client, roast_date=int(time.time()) - 14 * DAY)
    assert client.get("/api/bags").get_json()[0]["last_brew"] is None

    v1 = log_brew(client, bag_id=bag["id"])
    client.post(f"/api/brews/{v1['id']}/rate", json={"rating": "bitter"})
    v2 = log_brew(client, bag_id=bag["id"], parent_brew_id=v1["id"])

    listed = client.get("/api/bags").get_json()[0]
    assert listed["brew_count"] == 2
    assert listed["last_brew"]["id"] == v2["id"]
    assert listed["last_brew"]["version"] == 2
    assert listed["last_brew"]["chain_complete"] is False

    client.post(f"/api/brews/{v2['id']}/rate", json={"rating": "good"})
    assert client.get("/api/bags").get_json()[0]["last_brew"]["chain_complete"] is True


def test_flat_from_a_tired_bag_leaves_the_chain_alone(client):
    now = int(time.time())
    bag = make_bag(client, roast="dark", roast_date=now - 40 * DAY)
    brew = log_brew(client, bag_id=bag["id"])
    assert brew["bag_phase"] == "tired"
    r = client.post(f"/api/brews/{brew['id']}/rate", json={"rating": "flat"}).get_json()
    assert r["adjustment"]["lever"] is None
    assert r["next_chain"]["ratio_delta"] == 0.0


def test_rebuy_finishes_the_old_bag_and_starts_a_new_row(client):
    now = int(time.time())
    old = make_bag(client, roast_date=now - 30 * DAY, opened_at=now - 20 * DAY)
    brew = log_brew(client, bag_id=old["id"])

    r = client.post(f"/api/bags/{old['id']}/rebuy", json={"roast_date": now - 2 * DAY})
    assert r.status_code == 201
    new = r.get_json()
    assert new["id"] != old["id"]
    assert new["coffee_name"] == old["coffee_name"]
    assert new["opened_at"] is None
    assert new["freshness"]["phase"] == "resting"

    open_bags = client.get("/api/bags").get_json()
    assert [b["id"] for b in open_bags] == [new["id"]]
    all_bags = client.get("/api/bags?include_finished=1").get_json()
    finished = next(b for b in all_bags if b["id"] == old["id"])
    assert finished["finished_at"] is not None
    # The brew still points at the bag it actually came from.
    assert client.get("/api/history").get_json()[0]["bag_id"] == old["id"]
    assert client.get("/api/history").get_json()[0]["id"] == brew["id"]


def test_rebuy_of_unknown_bag_is_404(client):
    assert client.post("/api/bags/9999/rebuy", json={}).status_code == 404


# ─── Decided against ──────────────────────────────────────────────────────────

def test_no_route_deletes_aiden_profiles(client):
    """AidenClient.delete_profile exists; it must stay unrouted."""
    rules = {r.rule: r.methods for r in coffee_app.app.url_map.iter_rules()}
    for rule, methods in rules.items():
        if "aiden" in rule:
            assert "DELETE" not in methods, rule
