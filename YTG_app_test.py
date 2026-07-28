"""
YTG end-to-end smoke test.

Runs the full flow: create parent + offspring -> create guardian -> connect
offspring -> configure settings/restrictions -> turn guardian on -> scan ->
poll -> flush -> check reports -> award/spend points -> turn guardian off.

Every step is wrapped so a failure doesn't kill the run -- it gets logged to
ERRORS with its origin, and the script keeps going wherever it reasonably
can (steps that need an ID from a failed prior step are skipped, and that
skip is also logged).

Usage:
    pip install requests pillow --break-system-packages
    python ytg_smoke_test.py

Adjust BASE_URL and ENDPOINTS below if anything doesn't match your actual
route files -- several of these (restrictions, on/off) weren't in the route
files you'd shared, only in the markdown doc, so double check those first.
"""

import io
import sys
import requests
from pathlib import Path
from datetime import datetime

# ---------------------------------------------------------------------------
# Config -- adjust these if your actual routes differ
# ---------------------------------------------------------------------------

BASE_URL = "http://localhost:8000"

ENDPOINTS = {
    "signup": "/auth/signup",
    "create_guardian": "/guardians/",
    "add_connection": "/guardians/{guardian_id}/connections/add",
    "update_settings": "/guardians/{guardian_id}/settings/update",
    "add_restriction": "/guardians/{guardian_id}/restrictions/add",
    "guardian_on": "/sessions/{guardian_id}/on",
    "guardian_off": "/sessions/{guardian_id}/off",
    "sessions_by_guardian": "/sessions/guardian/{guardian_id}",
    "get_session": "/sessions/{session_id}",
    "scan": "/sessions/{session_id}/scan",
    "flush": "/sessions/{session_id}/flush",
    "reports": "/guardians/reports/{guardian_id}",
    "add_points": "/gameify/users/{user_id}/points/add",
    "remove_points": "/gameify/users/{user_id}/points/remove",
    "create_reward": "/gameify/rewards",
    "list_rewards": "/gameify/rewards",
    "buy_reward": "/gameify/users/{user_id}/rewards/buy",
}

TIMEOUT_SECONDS = 15

# ---------------------------------------------------------------------------
# Error tracking
# ---------------------------------------------------------------------------

ERRORS = []


def log_error(step: str, detail: str, response: requests.Response | None = None):
    entry = {
        "step": step,
        "detail": detail,
        "status_code": response.status_code if response is not None else None,
        "body": _safe_body(response) if response is not None else None,
        "time": datetime.utcnow().isoformat(),
    }
    ERRORS.append(entry)
    print(f"  [ERROR] {step}: {detail}")


def _safe_body(response: requests.Response):
    try:
        return response.json()
    except Exception:
        return response.text[:500]


def call(method: str, path: str, step: str, **kwargs):
    """Wraps a request call: returns the parsed JSON on success, None on failure.
    Logs any failure (network error, non-2xx status, bad JSON) to ERRORS."""
    url = f"{BASE_URL}{path}"
    try:
        resp = requests.request(method, url, timeout=TIMEOUT_SECONDS, **kwargs)
    except requests.RequestException as ex:
        log_error(step, f"Request failed: {ex}")
        return None

    if not resp.ok:
        log_error(step, f"HTTP {resp.status_code} from {method} {path}", resp)
        return None

    try:
        return resp.json()
    except ValueError:
        log_error(step, f"Response was not valid JSON from {method} {path}", resp)
        return None


def skip(step: str, reason: str):
    ERRORS.append({
        "step": step,
        "detail": f"SKIPPED -- {reason}",
        "status_code": None,
        "body": None,
        "time": datetime.utcnow().isoformat(),
    })
    print(f"  [SKIPPED] {step}: {reason}")


def section(title: str):
    print(f"\n=== {title} ===")


# ---------------------------------------------------------------------------
# Helper: build a small synthetic screenshot for the /scan step
# ---------------------------------------------------------------------------

def get_test_png_handdrawn() -> bytes:
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        print("  [WARN] Pillow not installed -- skipping synthetic image generation.")
        return b""
    # Create a 400x400 canvas with a patriotic blue background
    width, height = 400, 400
    image = Image.new("RGB", (width, height), color=(24, 43, 73))
    draw = ImageDraw.Draw(image)

    # 1. Suit / Torso (Navy Blue)
    draw.ellipse([50, 260, 350, 500], fill=(15, 25, 50))

    # 2. White Shirt Collar
    draw.polygon([(160, 260), (200, 310), (240, 260)], fill=(255, 255, 255))

    # 3. Signature Red Tie
    draw.polygon([(185, 275), (215, 275), (225, 400), (175, 400)], fill=(210, 30, 30))

    # 4. Face & Neck (Warm Tan/Gold Skin Tone)
    draw.ellipse([140, 150, 260, 280], fill=(245, 180, 125))  # Neck/Jaw
    draw.ellipse([130, 110, 270, 250], fill=(250, 190, 135))  # Main Face

    # 5. Signature Swoop Hair (Golden Yellow)
    # Base hair volume
    draw.ellipse([110, 70, 290, 160], fill=(245, 210, 70))
    # Swoop sweep to the side
    draw.polygon(
        [(110, 120), (140, 60), (280, 70), (300, 130), (230, 100)],
        fill=(255, 220, 80),
    )

    # Save image to an in-memory byte buffer
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")

    # Return the raw PNG bytes
    return buffer.getvalue()

def get_test_png(num:int=1) -> bytes:
    """
    Image 6:
    {'flagged': True, 
    'description': 'A social media video depicts two individuals in a physical altercation, 
    with the accompanying caption questioning an act of violence.', 
    'warning_active': True, 
    'points_awarded': False, 
    'points_lost': 0}
    
    """
    image_path = Path(__file__).parent / f"test_image{num}.png"

    return image_path.read_bytes()

def build_test_image_bytes() -> bytes:
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        print("  [WARN] Pillow not installed -- skipping synthetic image generation.")
        return b""

    img = Image.new("RGB", (400, 300), color=(30, 30, 30))
    draw = ImageDraw.Draw(img)
    draw.text((20, 20), "YTG smoke test screenshot", fill=(255, 255, 255))
    draw.text((20, 50), "This is placeholder content, not a real capture.", fill=(200, 200, 200))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Main flow
# ---------------------------------------------------------------------------

def main():
    print(f"Running YTG smoke test against {BASE_URL}")
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")

    # -----------------------------------------------------------------
    section("1. Create parent + offspring accounts")
    # -----------------------------------------------------------------
    parent = call("POST", ENDPOINTS["signup"], "signup:parent", json={
        "username": f"parent_{timestamp}",
        "email": f"parent_{timestamp}@example.com",
        "password": "SmokeTestPass123!",
    })
    parent_id = parent.get("id") if parent else None
    print(f"  parent_id = {parent_id}")

    offspring = call("POST", ENDPOINTS["signup"], "signup:offspring", json={
        "username": f"offspring_{timestamp}",
        "email": f"offspring_{timestamp}@example.com",
        "password": "SmokeTestPass123!",
    })
    offspring_id = offspring.get("id") if offspring else None
    print(f"  offspring_id = {offspring_id}")

    # -----------------------------------------------------------------
    section("2. Create Guardian")
    # -----------------------------------------------------------------
    guardian_id = None
    if parent_id:
        guardian = call("POST", ENDPOINTS["create_guardian"], "create_guardian", json={
            "owner_id": parent_id,
            "name": f"Smoke Test Household {timestamp}",
            "guardian_type": "family",
        })
        guardian_id = guardian.get("id") if guardian else None
        print(f"  guardian_id = {guardian_id}")
    else:
        skip("create_guardian", "parent_id missing from signup step")

    # -----------------------------------------------------------------
    section("3. Connect offspring to Guardian")
    # -----------------------------------------------------------------
    if guardian_id and offspring_id:
        call("POST", ENDPOINTS["add_connection"].format(guardian_id=guardian_id),
             "add_connection", json={"user_id": offspring_id, "relationship": "offspring"})
    else:
        skip("add_connection", "guardian_id or offspring_id missing")

    # -----------------------------------------------------------------
    section("4. Configure Guardian settings (strictness, messages, points penalty)")
    # -----------------------------------------------------------------
    if guardian_id:
        call("PATCH", ENDPOINTS["update_settings"].format(guardian_id=guardian_id),
             "update_settings", json={
                 "strictness": "harsh",
                 "language": "en",
                 "warning_message": "Please avoid this type of content, friend.",
                 "applause_message": "Nice work skipping that!",
             })
    else:
        skip("update_settings", "guardian_id missing")

    # -----------------------------------------------------------------
    section("5. Add restrictions")
    # -----------------------------------------------------------------
    if guardian_id:
        for restriction in ["gambling", "graphic violence", "politics"]:
            call("POST", ENDPOINTS["add_restriction"].format(guardian_id=guardian_id),
                 f"add_restriction:{restriction}", json={"restriction": restriction})
    else:
        skip("add_restriction", "guardian_id missing")

    # -----------------------------------------------------------------
    section("6. Turn Guardian on (creates sessions for connected users)")
    # -----------------------------------------------------------------
    if guardian_id:
        call("POST", ENDPOINTS["guardian_on"].format(guardian_id=guardian_id), "guardian_on")
    else:
        skip("guardian_on", "guardian_id missing")

    # -----------------------------------------------------------------
    section("7. Fetch the offspring's session")
    # -----------------------------------------------------------------
    session_id = None
    if guardian_id:
        sessions = call("GET", ENDPOINTS["sessions_by_guardian"].format(guardian_id=guardian_id),
                         "sessions_by_guardian")
        if sessions:
            match = next((s for s in sessions if s.get("user_id") == offspring_id), None)
            if match:
                session_id = match.get("id")
            elif sessions:
                # fall back to the first session if we can't match by user_id
                session_id = sessions[0].get("id")
                log_error("sessions_by_guardian",
                          "Could not match a session to offspring_id; used first session in list instead.")
        print(f"  session_id = {session_id}")
    else:
        skip("sessions_by_guardian", "guardian_id missing")

    # -----------------------------------------------------------------
    section("8. Upload a test screenshot for classification")
    # -----------------------------------------------------------------
    scan_result = None
    if session_id:
        image_bytes = get_test_png(6)
        if image_bytes:
            # try:
                resp = requests.post(
                    f"{BASE_URL}{ENDPOINTS['scan'].format(session_id=session_id)}",
                    files={"file": ("smoke_test.png", image_bytes, "image/png")},
                    timeout=TIMEOUT_SECONDS,
                )
                if resp.ok:
                    scan_result = resp.json()
                    print(f"  scan_result = {scan_result}")
                else:
                    log_error("scan", f"HTTP {resp.status_code}", resp)
            # except requests.RequestException as ex:
            #     log_error("scan", f"Request failed: {ex}")
        else:
            skip("scan", "Could not build test image (Pillow missing)")
    else:
        skip("scan", "session_id missing")

    # -----------------------------------------------------------------
    section("9. Poll session state")
    # -----------------------------------------------------------------
    if session_id:
        call("GET", ENDPOINTS["get_session"].format(session_id=session_id), "get_session")
    else:
        skip("get_session", "session_id missing")

    # -----------------------------------------------------------------
    section("10. Flush events into reports")
    # -----------------------------------------------------------------
    if session_id:
        call("POST", ENDPOINTS["flush"].format(session_id=session_id), "flush")
    else:
        skip("flush", "session_id missing")

    # -----------------------------------------------------------------
    section("11. Confirm reports show up under the Guardian")
    # -----------------------------------------------------------------
    if guardian_id:
        call("GET", ENDPOINTS["reports"].format(guardian_id=guardian_id), "reports")
    else:
        skip("reports", "guardian_id missing")

    # -----------------------------------------------------------------
    section("12. Simulate a completed avoidance timer (award points)")
    # -----------------------------------------------------------------
    if offspring_id:
        call("POST", ENDPOINTS["add_points"].format(user_id=offspring_id),
             "add_points", json={"amount": 50})
    else:
        skip("add_points", "offspring_id missing")

    # -----------------------------------------------------------------
    section("13. Simulate a points penalty (still viewing restricted content)")
    # -----------------------------------------------------------------
    if offspring_id:
        call("POST", ENDPOINTS["remove_points"].format(user_id=offspring_id),
             "remove_points", json={"amount": 10})
    else:
        skip("remove_points", "offspring_id missing")

    # -----------------------------------------------------------------
    section("14. Create + list rewards, then buy one")
    # -----------------------------------------------------------------
    reward = call("POST", ENDPOINTS["create_reward"], "create_reward", json={
        "name": f"Smoke Test Reward {timestamp}",
        "reward_amount": 5,
        "reward_cost": 20,
        "reward_type": "gift_card",
    })

    rewards_list = call("GET", ENDPOINTS["list_rewards"], "list_rewards")
    reward_id = None
    if rewards_list:
        target = next((r for r in rewards_list if r.get("name", "").startswith("Smoke Test Reward")), None)
        reward_id = target.get("id") if target else (rewards_list[0].get("id") if rewards_list else None)

    if offspring_id and reward_id:
        call("POST", ENDPOINTS["buy_reward"].format(user_id=offspring_id),
             "buy_reward", json={"reward_id": reward_id})
    else:
        skip("buy_reward", "offspring_id or reward_id missing")

    # -----------------------------------------------------------------
    section("15. Turn Guardian off (deletes sessions)")
    # -----------------------------------------------------------------
    if guardian_id:
        call("POST", ENDPOINTS["guardian_off"].format(guardian_id=guardian_id), "guardian_off")
    else:
        skip("guardian_off", "guardian_id missing")

    # -----------------------------------------------------------------
    section("Summary")
    # -----------------------------------------------------------------
    if not ERRORS:
        print("All steps completed with no errors or skips. ✅")
        return

    print(f"{len(ERRORS)} issue(s) encountered:\n")
    for i, err in enumerate(ERRORS, start=1):
        print(f"{i}. [{err['step']}] {err['detail']}")
        if err["status_code"]:
            print(f"   status_code: {err['status_code']}")
        if err["body"]:
            print(f"   body: {err['body']}")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted.")
        sys.exit(1)