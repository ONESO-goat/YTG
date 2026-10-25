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

Backend tests: `.venv/bin/python -m pytest tests`
