# LAN Manager Profile Manager

A web app for managing Remote Connect LAN Manager profiles (SSH, HTTP, HTTPS,
RDP, VNC and Serial) across your whole fleet at once — create them, copy them,
delete them, turn LAN Manager on or off, and clean up leftovers.

## What you need

- Python 3.9 or newer
- Your NCM API credentials:
  - `X_CP_API_ID`, `X_CP_API_KEY`, `X_ECM_API_ID`, `X_ECM_API_KEY`
  - `NCM_API_TOKEN` — **required**. LAN Manager profiles only exist in the v3
    API, and this token is what unlocks it. Without it the app can't do its job.

You can type the credentials into the app's Settings panel the first time you
run it, so you don't have to set anything up in advance.

## Start it

```bash
pip install -r requirements.txt
python serve.py
```

Then open **http://localhost:8000** in your browser.

If you installed the project's shared environment, activate it first:

```bash
source .venv/bin/activate && python3 -u serve.py    # macOS/Linux
.venv\Scripts\activate.bat && python -u serve.py    # Windows
```

The first time it loads, click the gear icon and enter your credentials, then
Apply. You can save them as a named profile so you don't retype them.

> The app runs on your own machine and has no login. Keep it on `localhost` —
> don't put it on a shared network, because anyone who could reach it would see
> your saved credentials.

## What you can do

- **Create a profile** — define one profile (say, an SSH profile on port 22)
  and push it to the routers or groups you pick.
- **Copy profiles** — grab one or more profiles off an existing router and push
  copies to other routers or groups. The original router isn't touched.
- **Delete profiles** — remove profiles by router, by group, or by profile
  name. Pick specific names or clear them all.
- **Disable LAN Manager** — switch LAN Manager off on routers or groups. Your
  profiles stay in place.
- **Clean up orphans** — find and delete profiles left behind by routers that
  no longer exist in your account.

## Good things to know

- **Nothing happens until you click Run.** Every action shows a preview first,
  so you can see exactly which routers will change.
- **You won't create duplicates.** When you push a profile, the app matches it
  to any existing profile with the same name (ignoring capitalization and extra
  spaces), updates that one in place, and clears out duplicates. Pushing the
  same thing twice is safe.
- **Pushing a profile turns LAN Manager on automatically** for every router it
  reaches. Deleting profiles never turns LAN Manager off — that's a separate
  action.
- **Push to a group, add routers later, push again** — only the new routers get
  changed.
- **Searches ignore capitalization**, including when you search by profile name.

## Fixing a profile you created wrong

1. Choose **Copy profile** and set the destination to **Profile name**, then
   search for the name.
2. Find the correct version and click **Use as source**.
3. Tick the wrong ones (whole groups or individual routers).
4. Click **Preview**, then **Run**.

## Logs

Every run is saved to a timestamped file in the `logs/` folder. The log records
each profile created, updated or deleted — including the old values of anything
that was replaced — so you always have a record of what changed.

## Settings

- **Credentials** — enter and save them under the gear icon.
- **Threads** (default 4) — how many routers the app works on at once. Higher is
  faster, but NCM allows roughly 500 API calls per minute and each router takes
  a handful, so leave it low for very large fleets.

## Troubleshooting

- **"Missing NCM_API_TOKEN"** — add your v3 token in the Settings panel. Profiles
  can't be read or written without it.
- **Port 8000 already in use** — another app is on that port. Stop it first
  (several apps in this collection share port 8000, so run them one at a time).
- **A router shows "router not in v2"** — that router isn't in your account's
  router list, so it can't receive pushes. It's skipped. These usually turn up
  under the orphan cleanup.
