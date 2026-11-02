# LAN Manager Profile Manager

Bulk-manage Remote Connect LAN Manager profiles (SSH, HTTP, HTTPS, RDP, VNC and
Serial) across a fleet.

| | |
|---|---|
| Port | 8095 (binds `127.0.0.1`) |
| Entry point | `serve.py` |
| APIs | v2 `routers` / `groups` / `accounts` (read-only); v3 `remote_connect_profiles`, `lan_manager_options` |
| Credentials | `X_CP_API_ID`, `X_CP_API_KEY`, `X_ECM_API_ID`, `X_ECM_API_KEY` **and `NCM_API_TOKEN`**. Profiles exist only in v3. |

## Run

```bash
source .venv/bin/activate && python3 -u web_apps/lan_manager_profile_manager/serve.py
```

Open http://localhost:8095. Credentials come from the environment or `.env`, or
you can enter them in the Settings panel (gear icon).

## Actions

- **Create profile**: define a profile and push it to routers, groups, or the
  routers found by a profile-name search.
- **Copy profile**: pick a source router (searchable), tick one or more of its
  profiles, and push them to a destination. The source router isn't changed.
- **Delete profiles**:
  - by router or group: choose which profile names to delete, or all of them
  - by profile name: tick whole variants, or individual routers within them
- **Disable LAN Manager**: turn LAN Manager off on routers or groups. Profiles
  are kept.
- **Orphaned profiles**: list and delete profiles whose router ID isn't in the
  v2 router list. These are profiles left behind after a router was
  unregistered or deleted.

## Rules

- **Searches ignore case.** That includes profile-name matching.
- **Pushes enable LAN Manager automatically.** Before writing any profiles, the
  app updates the router's `lan_manager_options` record if one exists and
  creates one if it doesn't.
- **Pushes never duplicate.** Existing profiles are matched by name, ignoring
  case and surrounding spaces:
  - no match: the profile is created
  - one or more matches of the same type: one is kept and updated in place (an
    already-identical one is preferred), and the rest are deleted
  - a match of a different type: the new profile is created first, then the old
    one is deleted
  - already identical: reported as *unchanged* and not written
- **Pushes are safe to repeat.** Push to a group, add routers to it later, and
  push again. Only the new routers change.
- **Deletes never touch LAN Manager.**
- **Variants** group profiles that have the same name and identical settings:
  type, exact name (case included), port, address, username and resolution.
  Variants are sorted largest first, since the most common one is usually the
  correct one.
- **Every router is re-read live when the run starts, and re-read after the
  write to verify it.** Previews use cached data.

## Fixing profiles that were created wrong

1. Choose **Copy profile**, set the destination to **Profile name**, and search
   the name.
2. On the correct variant, click **Use as source**.
3. Tick the wrong variants, or individual routers within them.
4. Click **Preview**, then **Run**.

## Logs

Each run writes `logs/lan_manager_<action>_<timestamp>.log`. Every create,
update and delete is logged along with the **previous values** of anything that
was replaced or deleted. The `logs/` folder is gitignored.

## Notes

- Routers that aren't in the v2 list can't receive pushes. They're skipped and
  shown as "router not in v2".
- Only groups that contain routers are listed. An account can hold thousands of
  empty groups, and listing them all made loading take minutes.
- There's no authentication. Anyone who can reach the port can read the saved
  credentials and change profiles, so keep the app on localhost.
- Threads are set in Settings (default 4). Each router takes 3–6 API calls, and
  NCM allows roughly 500 calls per minute.
