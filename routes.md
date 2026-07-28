# YTG API Reference

Base URL used throughout: `http://localhost:8000`
 All request bodies are JSON unless noted (the `/scan` endpoint uses multipart form data for the image upload).

---

## `routes/auth.py` — Authentication

### `POST /auth/signup`
Creates a new user account.

```bash
curl -X POST http://localhost:8000/auth/signup \
  -H "Content-Type: application/json" \
  -d '{
    "username": "julius",
    "email": "julius@example.com",
    "password": "SecurePass123!"
  }'
```

### `POST /auth/login`
Logs a user in with either username or email, plus password.

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "julius",
    "password": "SecurePass123!"
  }'
```

---

## `routes/user_routes.py` — Users

### `GET /users/`
Lists all users.

```bash
curl http://localhost:8000/users/
```

### `GET /users/{user_id}`
Fetches a single user by ID.

```bash
curl http://localhost:8000/users/03a79ebe-fc4b-4797-be1b-3d0886761de1
```

### `PATCH /users/{user_id}/name`
Updates a user's display name.

```bash
curl -X PATCH http://localhost:8000/users/USER_ID_HERE/name \
  -H "Content-Type: application/json" \
  -d '{
    "new_name": "Julius M."
  }'
```

### `PUT /users/{user_id}/password`
Changes a user's password.

```bash
curl -X PUT http://localhost:8000/users/USER_ID_HERE/password \
  -H "Content-Type: application/json" \
  -d '{
    "new_password": "NewSecurePass456!"
  }'
```

### `DELETE /users/{user_id}`
Deletes a user account.

```bash
curl -X DELETE http://localhost:8000/users/USER_ID_HERE
```

### `GET /users/guardian/{guardian_id}`
Lists all users connected to a given Guardian (e.g. all offspring/dependents under one family Guardian).

```bash
curl http://localhost:8000/users/guardian/GUARDIAN_ID_HERE
```

---

## `routes/guardians_routes.py` — Guardians

### `GET /guardians/all`
Lists all Guardians in the system.

```bash
curl http://localhost:8000/guardians/
```

### `POST /guardians/`
Creates a new Guardian (the container that activates supervision — family or personal).

```bash
curl -X POST http://localhost:8000/guardians/ \
  -H "Content-Type: application/json" \
  -d '{
    "owner_id": "USER_ID_HERE",
    "name": "The Smith Household",
    "guardian_type": "family"
  }'
```
`guardian_type` accepts `"family"` or `"personal"`.

### `GET /guardians/{guardian_id}`
Fetches a single Guardian by ID.

```bash
curl http://localhost:8000/guardians/03a79ebe-fc4b-4797-be1b-3d0886761de1 
```

### `GET /guardians/owner/{user_id}`
Fetches the Guardian owned by a given user.

```bash
curl http://localhost:8000/guardians/owner/USER_ID_HERE
```

### `DELETE /guardians/{guardian_id}`
Deletes a Guardian.

```bash
curl -X DELETE http://localhost:8000/guardians/GUARDIAN_ID_HERE
```

### `GET /guardians/{guardian_id}/connections`
Lists everyone connected to a Guardian (offspring, friends, supervisors — see `RelationshipType`).

```bash
curl http://localhost:8000/guardians/GUARDIAN_ID_HERE/connections
```

### `POST /guardians/{guardian_id}/connections/add`
Connects a user to a Guardian with a given relationship type.

```bash
curl -X POST http://localhost:8000/guardians/GUARDIAN_ID_HERE/connections/add \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "USER_ID_HERE",
    "relationship": "offspring"
  }'
```
`relationship` accepts `"offspring"`, `"friend"`, `"supervisor"`, or `"owner"`.

### `DELETE /guardians/{guardian_id}/connections/{user_id}`
Removes a user's connection to a Guardian.

```bash
curl -X DELETE http://localhost:8000/guardians/GUARDIAN_ID_HERE/connections/USER_ID_HERE
```

### `PUT /guardians/{guardian_id}/code`
Sets/changes the Guardian's access code (e.g. used to link a device or unlock settings).

```bash
curl -X PUT http://localhost:8000/guardians/GUARDIAN_ID_HERE/code \
  -H "Content-Type: application/json" \
  -d '{
    "code": 483920
  }'
```

### `POST /{guardian_id}/restrictions/add`
Add a restriction currently in the agents restrictions.
restrictions are the content the owner wants to avoid. The guardian should send warnings whenever content that falls into any restrictions is shown.

```bash
curl -X POST http://localhost:8000/guardians/GUARDIAN_ID_HERE/restrictions/add \
  -H "Content-Type: application/json" \
  -d '{
    "restriction": "politics"
  }'
```

### `POST /{guardian_id}/restrictions/remove`
Remove a restriction currently in the agents restrictions.
restrictions are the content the owner wants to avoid. The guardian should send warnings whenever content that falls into any restrictions is shown.

```bash
curl -X POST http://localhost:8000/guardians/GUARDIAN_ID_HERE/restrictions/remove \
  -H "Content-Type: application/json" \
  -d '{
    "restriction": "politics"
  }'
```

### `GET /guardians/{guardian_id}/settings`
Fetches (or creates, if missing) the Guardian's settings — strictness, language, custom messages.

```bash
curl http://localhost:8000/guardians/GUARDIAN_ID_HERE/settings
```

### `PATCH /guardians/{guardian_id}/settings/update`
Updates one or more Guardian settings fields. All fields optional — send only what's changing.

```bash
curl -X PATCH http://localhost:8000/guardians/GUARDIAN_ID_HERE/settings/update \
  -H "Content-Type: application/json" \
  -d '{
    "strictness": "harsh",
    "language": "en",
    "warning_message": "Please avoid this type of content honey",
    "applause_message": "Good job! Proud of you for skipping that."
  }'
```

### `GET /guardians/reports/{given_id}`
Fetches guardian reports either by Guardian ID or by owner (user) ID — tries Guardian first, falls back to owner.

```bash
curl http://localhost:8000/guardians/reports/GUARDIAN_OR_OWNER_ID_HERE
```

---

## `routes/session_routes.py` — Guardian Sessions

A **GuardianSession** is the live, per-user monitoring session — it holds the warning/timer state and pending points for one user under one Guardian.

### `GET /sessions/`
Lists all sessions.

```bash
curl http://localhost:8000/sessions/
```

## `POST /{guardian_id}/on`
Turns on the guardian, which automatically creates sessions for the users who are connected with the guardian

```bash
curl http://localhost:8000/GUARDIAN_ID_HERE/on
```


## `POST /{guardian_id}/off`
Turns off the guardian, which deletes all concurring sessions under the guardian/ 

```bash
curl http://localhost:8000/GUARDIAN_ID_HERE/off
```

### `POST /sessions/create`
Gets the existing session for a user+Guardian pair, or creates one if it doesn't exist yet. Call this once when the extension/app starts watching.

```bash
curl -X POST http://localhost:8000/sessions/create \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "USER_ID_HERE",
    "guardian_id": "GUARDIAN_ID_HERE"
  }'
```

### `GET /sessions/{session_id}`
Fetches a single session by ID — use this for cheap polling of current state (warning active? timer running?) without uploading a new screenshot.

```bash
curl http://localhost:8000/sessions/SESSION_ID_HERE
```

### `GET /sessions/guardian/{guardian_id}`
Lists all active sessions under a given Guardian (e.g. all currently-monitored dependents at once, for a parent dashboard).

```bash
curl http://localhost:8000/sessions/guardian/GUARDIAN_ID_HERE
```

### `DELETE /sessions/{session_id}`
Deletes/ends a session (e.g. on logout or after a period of inactivity).

```bash
curl -X DELETE http://localhost:8000/sessions/SESSION_ID_HERE
```

### `POST /sessions/{session_id}/scan` — core monitoring loop
Uploads a screenshot for classification. This is the endpoint the extension calls every 5-10s. **Multipart form data, not JSON** — the image goes in a `file` field.

```bash
curl -X POST http://localhost:8000/sessions/SESSION_ID_HERE/scan \
  -F "file=@/path/to/screenshot.png"
```

Response shape:
```json
{
  "flagged": true,
  "description": "A social media post referencing restricted content.",
  "warning_active": true,
  "points_awarded": false
}
```

### `POST /sessions/{session_id}/events`
Manually adds an event to a session's event log (mostly for testing — in normal flow, `/scan` adds events automatically when content is flagged).

```bash
curl -X POST http://localhost:8000/sessions/SESSION_ID_HERE/events \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Test event for manual QA",
    "time_duration": 180
  }'
```
`time_duration` is optional — omit it to get a randomized 140-300s duration.

### `POST /sessions/{session_id}/flush`
Converts all pending events on a session into permanent `GuardianReport`s (visible to the owner) and clears the session's event log. Call this when the guardian views their alert inbox, or periodically.

```bash
curl -X POST http://localhost:8000/sessions/SESSION_ID_HERE/flush
```

---

## `routes/gamify_routes.py` — Points & Rewards

### `PUT /gameify/users/{user_id}/points`
Sets a user's point balance to an exact value (overwrite, not add).

```bash
curl -X PUT http://localhost:8000/gameify/users/USER_ID_HERE/points \
  -H "Content-Type: application/json" \
  -d '{
    "amount": 500
  }'
```

### `POST /gameify/users/{user_id}/points/add`
Adds points to a user's balance (e.g. after a successful avoidance timer completes).

```bash
curl -X POST http://localhost:8000/gameify/users/USER_ID_HERE/points/add \
  -H "Content-Type: application/json" \
  -d '{
    "amount": 10
  }'
```

### `POST /gameify/users/{user_id}/points/remove`
Deducts points from a user's balance.

```bash
curl -X POST http://localhost:8000/gameify/users/USER_ID_HERE/points/remove \
  -H "Content-Type: application/json" \
  -d '{
    "amount": 50
  }'
```

### `GET /gameify/rewards`
Lists all rewards available in the store.

```bash
curl http://localhost:8000/gameify/rewards
```

### `GET /gameify/rewards/{reward_id}`
Fetches a single reward by ID.

```bash
curl http://localhost:8000/gameify/rewards/REWARD_ID_HERE
```

### `POST /gameify/rewards`
Creates a new reward in the store (admin/seeding endpoint).

```bash
curl -X POST http://localhost:8000/gameify/rewards \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Dunkin Gift Card",
    "reward_amount": 20,
    "reward_cost": 2500,
    "reward_type": "gift_card"
  }'
```

### `POST /gameify/users/{user_id}/rewards/buy`
Spends a user's points to purchase a reward.

```bash
curl -X POST http://localhost:8000/gameify/users/USER_ID_HERE/rewards/buy \
  -H "Content-Type: application/json" \
  -d '{
    "reward_id": "REWARD_ID_HERE"
  }'
```

### `POST /gameify/users/{user_id}/rewards/refund`
Refunds a previously purchased reward back to points (partial refund, per the `Gameify.refund_reward` logic).

```bash
curl -X POST http://localhost:8000/gameify/users/USER_ID_HERE/rewards/refund \
  -H "Content-Type: application/json" \
  -d '{
    "reward_id": "REWARD_ID_HERE"
  }'
```

---

## Suggested end-to-end test sequence

A realistic order to exercise the whole system manually:

1. `POST /auth/signup` → get a `user_id`
2. `POST /guardians/` (with `owner_id` = that user) → get a `guardian_id`
3. `POST /guardians/{guardian_id}/connections/add` → connect a second user as `"offspring"` if testing a family flow
4. `PATCH /guardians/{guardian_id}/settings/update` → set strictness/messages/points penalty check

current settings, its value, and description on its usage:
    *   strictness (string): How strict the agent should be with its responses and points system
        class StrictnessLevel(Enum):
            WEAK = "weak"
            NORMAL = "normal"
            HARSH = "harsh"

    *   language (string): Field(default=AvailableLanguages.ENGLISH.value), available languages
        class AvailableLanguages(Enum):
            ENGLISH = "en"
            SPANISH = "es"
            FRENCH = "fr"
            GERMAN = "de"
            ITALIAN = "it"
            PORTUGUESE = "pt"
            DUTCH = "nl"
            RUSSIAN = "ru"
            CHINESE = "zh"
            JAPANESE = "ja"
            KOREAN = "ko"

    *   custom_warning_messages (dict): 
        Two values 
        ```json
        {"warning": "warning message for content that deems harmful by owner demands", 
        "applause": "Message to applause the user if they listened to the warning"}
        ```
        
        The owner can edit the messages as an act of encoragement

    *   points_loss_enabled (boolean): whether the user loses points or not

    *   base_points_lost (number): The owner has control on how many points are lost

5. `POST /{guardian_id}/restrictions/add` → The owner sets restrictions for the guardian to detect
6. `POST /sessions/{guardian_id}/on` → start the agent, this creates sessions for users who are connected with the guradian

7. `POST /sessions/{session_id}/scan` → upload a test screenshot, see if it flags
8. `GET /sessions/{session_id}` → poll state
9. `POST /sessions/{session_id}/flush` → push any logged events into reports
10. `GET /guardians/reports/{guardian_id}` → confirm the report shows up
11. `POST /gameify/users/{user_id}/points/add` → simulate a completed avoidance timer. If points penalty check is true in guardian settings and the user is still viewing restricted content, the user loses point with the route `POST /gameify/users/{user_id}/points/remove`
12. `GET /gameify/rewards` → browse the store
13. `POST /gameify/users/{user_id}/rewards/buy` → spend points
14. `POST /sessions/{guardian_id}/off` → A guardian can stay on for long periods, but if the owner decides its the end of the cycle they can turn off the guardian which deletes all concurring sessions