from conftest import ADMIN, personal_setup, random_png, scan, signup

import services.gameify_service as gameify_service
import services.progress_service as progress_service
import services.session_services as session_services


# ------------------------------------------------------------------------------
# Auth
# ------------------------------------------------------------------------------
def test_signup_login_me_never_expose_password(client):
    headers, user = signup(client)
    assert "password" not in user

    r = client.post("/auth/login", json={"identifier": user["username"].upper(), "password": "Password123"})
    assert r.status_code == 200
    assert "password" not in r.json()["user"]

    r = client.post("/auth/login", json={"identifier": user["email"], "password": "Password123"})
    assert r.status_code == 200

    me = client.get("/auth/me", headers=headers).json()
    assert me["user"]["id"] == user["id"]
    assert me["guardian"] is None


def test_wrong_password_and_missing_token(client):
    _, user = signup(client)
    r = client.post("/auth/login", json={"identifier": user["username"], "password": "Nope12345678"})
    assert r.status_code == 401
    assert client.get("/auth/me").status_code == 401
    assert client.get("/auth/me", headers={"Authorization": "Bearer garbage"}).status_code == 401


def test_weak_password_rejected(client):
    r = client.post(
        "/auth/signup",
        json={
            "username": "weakling",
            "email": "weak@example.com",
            "password": "short",
            "user_type": "individual",
        },
    )
    assert r.status_code == 400


def test_admin_endpoints_need_key(client):
    headers, user = signup(client)
    assert (
        client.put(f"/gameify/users/{user['id']}/points", json={"amount": 5}, headers=headers).status_code
        == 403
    )
    assert (
        client.post(
            "/gameify/rewards", json={"name": "x", "reward_amount": 1, "reward_cost": 1}, headers=headers
        ).status_code
        == 403
    )


# ------------------------------------------------------------------------------
# Scanning
# ------------------------------------------------------------------------------
def test_clean_minutes_earn_points(client, clock):
    headers, user, guardian, sess = personal_setup(client)
    assert guardian["guardian_type"] == "personal" and guardian["on"] is True

    first = scan(client, headers, sess["id"], seed=1)
    assert first["flagged"] is False and first["points_awarded"] == 0
    clock.advance(61)
    second = scan(client, headers, sess["id"], seed=2)
    assert second["points_awarded"] == 10 and second["xp_awarded"] == 10
    # +20 came from the "First steps" achievement when the session started
    assert second["currency"] == 30


def test_heeding_a_warning_earns_avoidance_points(client, clock):
    headers, user, guardian, sess = personal_setup(client)
    client.post("/dev/simulate", headers=headers, json={"category": "gore", "scans": 2})

    r = scan(client, headers, sess["id"], seed=10)
    assert r["flagged"] and r["warning_active"] and r["category"] == "gore"
    clock.advance(5)
    r = scan(client, headers, sess["id"], seed=11)
    assert r["flagged"] and r["points_lost"] == 0

    # Moves away and stays away for the avoidance window
    clock.advance(5)
    r = scan(client, headers, sess["id"], seed=12)
    assert not r["flagged"] and r["warning_active"]
    clock.advance(session_services.AVOIDANCE_SECONDS)
    r = scan(client, headers, sess["id"], seed=13)
    assert r["warning_active"] is False
    # The avoidance bonus plus the "Walked away" achievement
    walked_away = progress_service.ACHIEVEMENTS_BY_CODE["first_heed"].points
    assert r["points_awarded"] == progress_service.AVOIDANCE_POINTS + walked_away
    assert any(e["type"] == "achievement" and e["title"] == "Walked away" for e in r["events"])

    reports = client.get(f"/guardians/{guardian['id']}/reports", headers=headers).json()
    assert any("gore" in rep["content"] for rep in reports)


def test_ignoring_a_warning_costs_points(client, clock):
    headers, user, guardian, sess = personal_setup(client)
    client.put(f"/gameify/users/{user['id']}/points", json={"amount": 100}, headers=ADMIN)
    client.patch(
        f"/guardians/{guardian['id']}/settings",
        headers=headers,
        json={"base_points_lost": 10, "strictness": "harsh"},
    )
    client.post("/dev/simulate", headers=headers, json={"category": "hate speech", "scans": 20})

    scan(client, headers, sess["id"], seed=20)
    clock.advance(session_services.IGNORE_THRESHOLD_SECONDS)
    r = scan(client, headers, sess["id"], seed=21)
    assert r["points_lost"] == 20  # 10 * harsh multiplier 2.0
    assert r["currency"] == 80

    # Not again straight away...
    clock.advance(10)
    r = scan(client, headers, sess["id"], seed=22)
    assert r["points_lost"] == 0
    # ...but every minute it keeps being ignored, up to 3 times per warning
    clock.advance(session_services.REPEAT_PENALTY_SECONDS)
    assert scan(client, headers, sess["id"], seed=25)["points_lost"] == 20
    clock.advance(session_services.REPEAT_PENALTY_SECONDS)
    assert scan(client, headers, sess["id"], seed=26)["points_lost"] == 20
    clock.advance(session_services.REPEAT_PENALTY_SECONDS)
    assert scan(client, headers, sess["id"], seed=27)["points_lost"] == 0

    # Walking away after ignoring gives no avoidance reward
    client.post("/dev/simulate", headers=headers, json={"scans": 0})
    scan(client, headers, sess["id"], seed=23)
    clock.advance(session_services.AVOIDANCE_SECONDS)
    r = scan(client, headers, sess["id"], seed=24)
    assert r["warning_active"] is False and r["points_awarded"] == 0


def test_idle_screen_earns_nothing_then_shuts_down(client, clock):
    headers, user, guardian, sess = personal_setup(client)
    scan(client, headers, sess["id"], seed=98)  # starts the clean-minute timer
    results = []
    for _ in range(session_services.IDLE_SHUTDOWN_FRAMES):
        clock.advance(5)
        results.append(scan(client, headers, sess["id"], seed=98))
    assert all(r["idle"] for r in results)
    assert sum(r["points_awarded"] for r in results) == 0
    assert results[-1]["shutdown"] is True
    assert all(not r["shutdown"] for r in results[:-1])

    # The session is stopped, so further scans are refused until restarted
    r = client.post(
        f"/sessions/{sess['id']}/scan", headers=headers, files={"file": ("f.png", random_png(5), "image/png")}
    )
    assert r.status_code == 409


def test_scan_rejects_non_images(client):
    headers, user, guardian, sess = personal_setup(client)
    r = client.post(
        f"/sessions/{sess['id']}/scan",
        headers=headers,
        files={"file": ("f.png", b"not an image", "image/png")},
    )
    assert r.status_code == 400


# ------------------------------------------------------------------------------
# Family guardians & access control
# ------------------------------------------------------------------------------
def test_family_flow_and_access_control(client, clock):
    owner_h, owner = signup(client, "caregiver")
    kid_h, kid = signup(client, "dependent")
    stranger_h, _ = signup(client, "individual")

    guardian = client.post("/guardians", headers=owner_h, json={"name": "Family"}).json()
    assert guardian["guardian_type"] == "family"

    # Dependents can't create guardians and can't start without a connection
    assert client.post("/guardians", headers=kid_h, json={"name": "x"}).status_code == 400
    assert client.post("/sessions/start", headers=kid_h, json={}).status_code == 400

    r = client.post(
        f"/guardians/{guardian['id']}/members", headers=owner_h, json={"user_number_id": kid["number_id"]}
    )
    assert r.status_code == 201, r.text
    me = client.get("/auth/me", headers=kid_h).json()
    assert me["guardian"]["id"] == guardian["id"] and me["is_guardian_owner"] is False

    # Kid can read settings but not change them
    assert client.get(f"/guardians/{guardian['id']}/settings", headers=kid_h).status_code == 200
    assert (
        client.patch(
            f"/guardians/{guardian['id']}/settings", headers=kid_h, json={"strictness": "weak"}
        ).status_code
        == 403
    )
    # Strangers see nothing
    assert client.get(f"/guardians/{guardian['id']}", headers=stranger_h).status_code == 403
    assert client.get(f"/guardians/{guardian['id']}/members", headers=stranger_h).status_code == 403

    sess = client.post("/sessions/start", headers=kid_h, json={}).json()["session"]
    # The owner can see the session but not send scans for the kid; strangers can't see it
    assert client.get(f"/sessions/{sess['id']}", headers=owner_h).status_code == 200
    assert client.get(f"/sessions/{sess['id']}", headers=stranger_h).status_code == 403
    r = client.post(
        f"/sessions/{sess['id']}/scan", headers=owner_h, files={"file": ("f.png", random_png(1), "image/png")}
    )
    assert r.status_code == 403

    client.post("/dev/simulate", headers=kid_h, json={"category": "violence", "scans": 1})
    scan(client, kid_h, sess["id"], seed=40)
    reports = client.get(f"/guardians/{guardian['id']}/reports", headers=owner_h).json()
    assert any(kid["name"] in rep["content"] for rep in reports)

    members = client.get(f"/guardians/{guardian['id']}/members", headers=owner_h).json()
    assert members[0]["user"]["id"] == kid["id"] and members[0]["progress"]["today"]["warnings_total"] == 1

    # Turning the guardian off stops the kid's session
    assert client.post(f"/guardians/{guardian['id']}/off", headers=owner_h).json()["on"] is False
    r = client.post(
        f"/sessions/{sess['id']}/scan", headers=kid_h, files={"file": ("f.png", random_png(41), "image/png")}
    )
    assert r.status_code == 409
    assert client.post("/sessions/start", headers=kid_h, json={}).status_code == 409


def test_restrictions_crud(client):
    headers, user, guardian, _ = personal_setup(client)
    r = client.post(
        f"/guardians/{guardian['id']}/restrictions", headers=headers, json={"restriction": "Gambling"}
    )
    assert r.status_code == 200 and "gambling" in r.json()["custom"]
    r = client.delete(
        f"/guardians/{guardian['id']}/restrictions", headers=headers, params={"restriction": "gambling"}
    )
    assert r.status_code == 200 and r.json()["custom"] == []


# ------------------------------------------------------------------------------
# Shop
# ------------------------------------------------------------------------------
def test_shop_buy_and_refund(client, clock):
    headers, user = signup(client)
    rewards = client.get("/gameify/rewards", headers=headers).json()
    card = next(r for r in rewards if r["type"] == "gift_card")
    assert client.post(f"/gameify/rewards/{card['id']}/buy", headers=headers).status_code == 400

    client.put(f"/gameify/users/{user['id']}/points", json={"amount": card["cost"]}, headers=ADMIN)
    r = client.post(f"/gameify/rewards/{card['id']}/buy", headers=headers)
    # Spent everything, then the "Treat yourself" achievement paid out
    treat = progress_service.ACHIEVEMENTS_BY_CODE["first_purchase"].points
    assert r.status_code == 200 and r.json()["currency"] == treat
    assert any(e["title"] == "Treat yourself" for e in r.json()["events"])
    owned = client.get("/gameify/me/rewards", headers=headers).json()
    assert owned[0]["reward"]["id"] == card["id"]

    r = client.post(f"/gameify/me/rewards/{owned[0]['id']}/refund", headers=headers)
    assert r.status_code == 200
    # The achievement bonus stays; the refund returns 5/6 of the cost
    expected = (
        int(card["cost"] * gameify_service.REFUND_RATE)
        + progress_service.ACHIEVEMENTS_BY_CODE["first_purchase"].points
    )
    assert r.json()["currency"] == expected


def test_refund_window(client, clock):
    headers, user = signup(client)
    card = next(r for r in client.get("/gameify/rewards", headers=headers).json() if r["type"] == "gift_card")
    client.put(f"/gameify/users/{user['id']}/points", json={"amount": card["cost"]}, headers=ADMIN)
    client.post(f"/gameify/rewards/{card['id']}/buy", headers=headers)
    owned = client.get("/gameify/me/rewards", headers=headers).json()[0]
    clock.advance(25 * 3600)
    assert client.post(f"/gameify/me/rewards/{owned['id']}/refund", headers=headers).status_code == 400
