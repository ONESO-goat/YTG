# Your Truest Guardian

---

## Quick shot summary

Inequality is the main aggressor when it comes to poverty which leads to hunger, mental health issues, overall peace, etc

## Ideas

Bot stalks over the users phone (No stealing info or hoarding)
If the person, lets say online, decides the post a very mean comment, the bot is activates warning them and tries to stray them away from the habit. You can still post, but a reward is adding to benefit leaving the poor behavior.

## Why

Social media is the hub where inequal teaching or opinions are expressed and sticked on. We can not atop inequality, but we can suppress it, espessally for those of a young age.

## How it works

* Set up bot
* change some settings (How harsh it is, disable, etc)
* scroll on a platform (tiktok, twitter, instagram, etc)
* If any harmful content is shown, like a trend of disrespectful comments or the user adding a poor comment themself, the bot appears and either tells them to move away or to avoid the content
* If avoided, gain points (fake currency) that allows you to buy gift cards, passes, etc

## Running locally

Copy `.env.example` to `.env` and set `JWT_SECRET`. With `AI_BACKEND=stub`, no Ollama or Gemini is needed:
every scan comes back clean, and the Session page has a developer panel to simulate flagged content.

```bash
python -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn main:app --reload --port 8000
```

```bash
npm install
npm run dev
```

The app runs at http://localhost:8080 and the API docs at http://localhost:8000/docs.

Checks:

```bash
.venv/bin/python -m pytest
.venv/bin/ruff check . && .venv/bin/ruff format --check .
npm run lint && npx tsc --noEmit
```

The database schema is brought up to date on startup (`db.py`): new columns and indexes are added and retired ones dropped.

## Game rules

Tunable constants live in `services/progress_service.py`, `services/session_services.py` and `services/gameify_service.py`.

* **Points** are spent in the shop. **XP** is earned alongside points but never spent or lost, so levels never go down.
* A clean minute earns 10 points and 10 XP, up to 600 a day. An unchanged screen earns nothing, and after ~5 minutes the session stops.
* Moving away from flagged content for 15 seconds after a warning earns a 25 point bonus (5 bonuses a day).
* Staying on flagged content for 30 seconds after a warning costs points (on by default, set per guardian). The penalty repeats every minute it continues, up to 3 times per warning, and doubles after 5 warnings in a day. Balances never go negative.
* The daily goal is 15 clean minutes. It pays a 50 point bonus and extends your streak. Streak freezes from the shop (max 2) cover missed days.
* 15 badges pay one-time bonuses. Leaderboards rank XP over the last 7 days: family members see their family, and individuals can opt in to the global board. Kids never appear on the global board.
* Gift cards can be refunded within 24 hours for 5/6 of the cost. Streak freezes can't be refunded.
