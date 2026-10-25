import itertools

from conftest import ADMIN, personal_setup, scan, signup

import services.progress_service as ps
import services.session_services as ss

_seeds = itertools.count(1000)


def clean_minutes(client, headers, session_id, clock, minutes):
    """Scan through `minutes` clean minutes. Returns all scan results."""
    results = [scan(client, headers, session_id, next(_seeds))]
    for _ in range(minutes):
        clock.advance(61)
        results.append(scan(client, headers, session_id, next(_seeds)))
    return results


def progress(client, headers):
    return client.get("/progress/me", headers=headers).json()


def restart(client, headers):
    """Sessions are per user, so starting again just resumes the same one."""
    return client.post("/sessions/start", headers=headers, json={}).json()["session"]


def test_first_session_unlocks_an_achievement(client, clock):
    headers, user = signup(client)
    client.post("/guardians", headers=headers, json={"name": "Mine"})
    r = client.post("/sessions/start", headers=headers, json={}).json()
    assert [e["title"] for e in r["events"]] == ["First steps"]
    # Starting an already running session doesn't count again
    assert client.post("/sessions/start", headers=headers, json={}).json()["events"] == []


def test_daily_goal_starts_a_streak(client, clock):
    headers, user, guardian, sess = personal_setup(client)
    results = clean_minutes(client, headers, sess["id"], clock, ps.DAILY_GOAL_MINUTES)
    events = [e for r in results for e in r["events"]]
    assert any(e["type"] == "goal" for e in events)
    p = progress(client, headers)
    assert p["today"]["goal_completed"] and p["streak"]["current"] == 1 and p["streak"]["done_today"]
    assert p["xp"] == p["today"]["xp_earned"]


def test_clean_minute_points_are_capped_per_day(client, clock):
    headers, user, guardian, sess = personal_setup(client)
    minutes = ps.DAILY_MINUTE_POINTS_CAP // ps.CLEAN_MINUTE_POINTS + 3
    results = clean_minutes(client, headers, sess["id"], clock, minutes)
    p = progress(client, headers)
    assert p["today"]["minute_points"] == ps.DAILY_MINUTE_POINTS_CAP
    assert p["today"]["clean_minutes"] == minutes
    # The last minutes only earned nothing (achievement bonuses aside)
    assert all(r["points_awarded"] == 0 for r in results[-3:] if not r["events"])


def test_level_ups_are_reported(client, clock):
    headers, user, guardian, sess = personal_setup(client)
    results = clean_minutes(client, headers, sess["id"], clock, 12)
    level_ups = [e for r in results for e in r["events"] if e["type"] == "level_up"]
    assert level_ups and level_ups[0]["title"] == "Level 2!"
    assert progress(client, headers)["level"] >= 2


def test_avoidance_bonus_is_capped_per_day(client, clock):
    headers, user, guardian, sess = personal_setup(client)
    bonuses = []
    for _ in range(ps.MAX_AVOIDANCE_BONUSES_PER_DAY + 1):
        client.post("/dev/simulate", headers=headers, json={"category": "gore", "scans": 1})
        scan(client, headers, sess["id"], next(_seeds))  # flagged
        clock.advance(5)
        scan(client, headers, sess["id"], next(_seeds))  # moved away
        clock.advance(ss.AVOIDANCE_SECONDS)
        r = scan(client, headers, sess["id"], next(_seeds))
        assert r["warning_active"] is False
        bonus_events = sum(e["points"] for e in r["events"] if e["type"] == "achievement")
        bonuses.append(r["points_awarded"] - bonus_events)
    assert bonuses[:-1] == [ps.AVOIDANCE_POINTS] * ps.MAX_AVOIDANCE_BONUSES_PER_DAY
    assert bonuses[-1] == 0
    p = progress(client, headers)
    assert p["today"]["warnings_heeded"] == ps.MAX_AVOIDANCE_BONUSES_PER_DAY + 1
    assert p["today"]["avoidance_bonuses_left"] == 0


def test_streak_freezes_cover_missed_days(client, clock):
    headers, user, guardian, sess = personal_setup(client)
    clean_minutes(client, headers, sess["id"], clock, ps.DAILY_GOAL_MINUTES)  # day 1

    clock.advance(24 * 3600)
    clean_minutes(client, headers, sess["id"], clock, ps.DAILY_GOAL_MINUTES)  # day 2
    assert progress(client, headers)["streak"]["current"] == 2

    # Buy a freeze, then skip a day
    client.put(f"/gameify/users/{user['id']}/points", json={"amount": 5000}, headers=ADMIN)
    freeze = next(
        r for r in client.get("/gameify/rewards", headers=headers).json() if r["type"] == "streak_freeze"
    )
    assert client.post(f"/gameify/rewards/{freeze['id']}/buy", headers=headers).status_code == 200
    assert progress(client, headers)["streak"]["freezes"] == 1

    clock.advance(2 * 24 * 3600)
    p = progress(client, headers)
    assert p["streak"]["current"] == 2 and p["streak"]["at_risk"]  # protected, but not done today
    results = clean_minutes(client, headers, sess["id"], clock, ps.DAILY_GOAL_MINUTES)
    assert any(e["type"] == "freeze_used" for r in results for e in r["events"])
    p = progress(client, headers)
    assert p["streak"]["current"] == 3 and p["streak"]["freezes"] == 0

    # Missing two days with no freezes breaks it
    clock.advance(3 * 24 * 3600)
    assert progress(client, headers)["streak"]["current"] == 0
    clean_minutes(client, headers, sess["id"], clock, ps.DAILY_GOAL_MINUTES)
    p = progress(client, headers)
    assert p["streak"]["current"] == 1 and p["streak"]["best"] == 3


def test_streak_freeze_limit(client, clock):
    headers, user = signup(client)
    client.put(f"/gameify/users/{user['id']}/points", json={"amount": 100_000}, headers=ADMIN)
    freeze = next(
        r for r in client.get("/gameify/rewards", headers=headers).json() if r["type"] == "streak_freeze"
    )
    for _ in range(ps.MAX_STREAK_FREEZES):
        assert client.post(f"/gameify/rewards/{freeze['id']}/buy", headers=headers).status_code == 200
    r = client.post(f"/gameify/rewards/{freeze['id']}/buy", headers=headers)
    assert r.status_code == 400 and "at most" in r.json()["detail"]


def test_days_follow_the_users_timezone(client, clock):
    headers, user, guardian, sess = personal_setup(client)
    assert (
        client.patch("/progress/me/preferences", headers=headers, json={"timezone": "Not/AZone"}).status_code
        == 400
    )
    # 12:00 UTC on Jan 1 is already Jan 2 in Kiritimati (UTC+14)
    p = client.patch(
        "/progress/me/preferences", headers=headers, json={"timezone": "Pacific/Kiritimati"}
    ).json()
    assert p["today"]["day"] == "2026-01-02"


def test_achievements_list(client, clock):
    headers, user, guardian, sess = personal_setup(client)
    achievements = client.get("/progress/me/achievements", headers=headers).json()
    assert len(achievements) == len(ps.ACHIEVEMENTS)
    first = next(a for a in achievements if a["code"] == "first_session")
    assert first["unlocked_at"] and first["progress"] == 1
    hour = next(a for a in achievements if a["code"] == "clean_hour")
    assert hour["unlocked_at"] is None and hour["progress"] == 0


def test_leaderboards(client, clock):
    owner_h, _ = signup(client, "caregiver")
    guardian = client.post("/guardians", headers=owner_h, json={"name": "Fam"}).json()
    kids = [signup(client, "dependent") for _ in range(2)]
    for _, kid in kids:
        client.post(
            f"/guardians/{guardian['id']}/members", headers=owner_h, json={"user_number_id": kid["number_id"]}
        )

    # The second kid earns more this week
    kid_h, kid = kids[1]
    sess = restart(client, kid_h)
    clean_minutes(client, kid_h, sess["id"], clock, 3)

    board = client.get("/progress/leaderboard", params={"scope": "family"}, headers=kids[0][0]).json()
    assert [e["username"] for e in board["entries"]] == [kids[1][1]["username"], kids[0][1]["username"]]
    assert board["entries"][1]["is_me"] and board["visible"]
    # The owner sees the board but isn't on it
    owner_board = client.get("/progress/leaderboard", params={"scope": "family"}, headers=owner_h).json()
    assert len(owner_board["entries"]) == 2 and not owner_board["visible"]

    # Kids can't join the global board
    r = client.patch("/progress/me/preferences", headers=kid_h, json={"show_on_leaderboard": True})
    assert r.status_code == 400
    # Individuals are hidden until they opt in
    solo_h, solo = signup(client)
    board = client.get("/progress/leaderboard", headers=solo_h).json()
    assert not board["visible"] and board["me"]["username"] == solo["username"]
    assert all(e["username"] != kid["username"] for e in board["entries"])
    client.patch("/progress/me/preferences", headers=solo_h, json={"show_on_leaderboard": True})
    board = client.get("/progress/leaderboard", headers=solo_h).json()
    assert board["visible"] and any(e["is_me"] for e in board["entries"])

    # A personal account has no family board
    assert client.get("/progress/leaderboard", params={"scope": "family"}, headers=solo_h).status_code == 404


def test_purchases_cannot_overspend(client, clock):
    headers, user = signup(client)
    card = next(r for r in client.get("/gameify/rewards", headers=headers).json() if r["type"] == "gift_card")
    client.put(f"/gameify/users/{user['id']}/points", json={"amount": card["cost"]}, headers=ADMIN)
    first = client.post(f"/gameify/rewards/{card['id']}/buy", headers=headers)
    second = client.post(f"/gameify/rewards/{card['id']}/buy", headers=headers)
    assert first.status_code == 200 and second.status_code == 400
    assert len(client.get("/gameify/me/rewards", headers=headers).json()) == 1


def test_family_members_include_progress(client, clock):
    owner_h, _ = signup(client, "caregiver")
    guardian = client.post("/guardians", headers=owner_h, json={"name": "Fam"}).json()
    kid_h, kid = signup(client, "dependent")
    client.post(
        f"/guardians/{guardian['id']}/members", headers=owner_h, json={"user_number_id": kid["number_id"]}
    )
    sess = restart(client, kid_h)
    clean_minutes(client, kid_h, sess["id"], clock, 2)
    member = client.get(f"/guardians/{guardian['id']}/members", headers=owner_h).json()[0]
    assert member["progress"]["today"]["clean_minutes"] == 2
    assert member["progress"]["xp"] > 0


def test_dev_grant_levels_up(client, clock):
    headers, user = signup(client)
    r = client.post("/dev/grant", headers=headers, json={"xp": 100}).json()
    assert [e["title"] for e in r["events"]] == ["Level 2!"]
    assert progress(client, headers)["level"] == 2
