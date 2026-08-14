# Host Identity Copier

Copy the host address identities (`identities.ip`) from a master NCM group to any
number of destination groups.

<img width="1369" height="636" alt="image" src="https://github.com/user-attachments/assets/ec0737a6-5ba0-4474-8c1b-2ce81ac7b0f4" />
<img width="1369" height="749" alt="image" src="https://github.com/user-attachments/assets/64d65def-63cb-49ce-92aa-de8429097110" />
<img width="1369" height="841" alt="image" src="https://github.com/user-attachments/assets/f66b25bc-b9f3-4fdb-8bfe-e669946c8762" />
<img width="1369" height="841" alt="image" src="https://github.com/user-attachments/assets/328de778-8173-4434-a761-f760ed6ecb70" />


Port: **8070**

```bash
.venv/bin/python web_apps/host_identity_copier/serve.py           # macOS/Linux
.venv\Scripts\python.exe web_apps\host_identity_copier\serve.py   # Windows
```

Then open http://localhost:8070

## Defaults

| Selection | Default | Behavior |
|-----------|---------|----------|
| Source group | name contains `Base` (case-insensitive) | One match is selected and read automatically. Several matches show a picker. No match leaves the search box for you. |
| Destination groups | name contains `(R)` (restricted) | Every match is pre-selected, **except the source group**. |

The Base group's name often contains `(R)` too, so it would match the destination
pattern. It is excluded from the destination list on the frontend and stripped
from the destination list again on the backend, so it can never be written to.

Both patterns are plain case-insensitive substring matches, so `(R)` is matched
literally rather than as a regex group. Saved selections from a previous run take
precedence over these defaults; the **Defaults** button clears the saved job and
re-applies them.

## Workflow

1. **Credentials** — click the gear icon and enter `X_CP_API_ID`, `X_CP_API_KEY`,
   `X_ECM_API_ID`, `X_ECM_API_KEY`. They are written to `config.json` in this
   folder and loaded on the next run. Named profiles can also be saved there.
   Real environment variables take precedence over the stored values.
2. **Source group** — resolved from the `Base` default, or searched manually. The
   search box autocompletes on group names and accepts wildcards (`*Base*`).
   Submitting reads the group config and extracts `identities.ip`, listing each
   identity with its addresses.
3. **Destination groups** — pre-filled with the `(R)` matches. Adjust with the
   search box (`*(R)*`, `PROD-*`, `SITE-?`), **Select All Matching**, individual
   checkboxes, or the removable chips. The source group is never a destination.
4. **Copy** — pick a mode, optionally dry run first. The dry run reports exactly
   what would be added, updated and removed per group without sending anything.
   Results are reported per group and can be exported to CSV.

## Copy modes

| Mode | Behavior |
|------|----------|
| Mirror (default) | Each destination ends up with exactly the source's identities. Surplus addresses and destination-only identities are removed. |
| Additive | Adds and updates only. Removes nothing. |

Mirror mode reads each destination group's current config first so it can work out
what to prune, so a push costs one GET plus one PATCH per destination group. A
destination already matching the source is skipped without a write.

### How mirroring works

Both modes use `PATCH /api/v2/groups/{id}/` with the same two-element diff format
NCM's own UI sends, `[updates, removals]`.

Updates set each source identity, keyed by UUID with that UUID repeated in `_id_`
(NCM rejects UUID-keyed entries without it), and the address list as an
index-keyed object:

```json
[
    {
        "identities": {
            "ip": {
                "0897fa24-b4a4-4aa2-9cab-0bed9507c233": {
                    "_id_": "0897fa24-b4a4-4aa2-9cab-0bed9507c233",
                    "name": "IPs",
                    "members": { "0": { "address": "1.2.3.4" }, "1": { "address": "2.3.4.5" } }
                }
            }
        }
    },
    []
]
```

Removals prune what the destination has and the source does not. Array elements
are addressed by **integer** index:

```json
[
    {},
    [
        ["identities", "ip", "0897fa24-b4a4-4aa2-9cab-0bed9507c233", "members", 2],
        ["identities", "ip", "c9b4c44c-0c68-447e-b64d-1bcb3fac0c73"]
    ]
]
```

The first path drops a surplus address; the second drops an entire
destination-only identity. Surplus indices are emitted highest-first so the paths
stay valid whether NCM resolves them against the original config or applies them
sequentially with reindexing.

Nothing outside `identities.ip` is touched, and the source group is never written
to.

## Config file

`config.json` (created on first use, `0600` on POSIX, gitignored):

```json
{
  "credentials": { "X_CP_API_ID": "...", "X_CP_API_KEY": "...", "X_ECM_API_ID": "...", "X_ECM_API_KEY": "..." },
  "profiles": { "Production": { "X_CP_API_ID": "..." } },
  "source_group": { "id": 123456, "name": "Base Group" },
  "destination_groups": [ { "id": 234567, "name": "Store 12 (R)" } ],
  "destination_filter": "(R)",
  "push_mode": "mirror"
}
```

The source group is saved when you extract; destinations, search pattern and copy
mode are saved when you push or click **Save Selection**. On the next run the app
restores all of it so the same job can be repeated.

## Expected source config

The app reads the group's `configuration` diff — a two element list of
`[updates, removals]` — and pulls `identities.ip` out of the updates dict:

```json
[
    {
        "identities": {
            "ip": {
                "6961bb08-2b86-4766-863c-dd682962106f": {
                    "_id_": "6961bb08-2b86-4766-863c-dd682962106f",
                    "name": "IPs",
                    "members": {
                        "0": { "address": "1.2.3.4" }
                    },
                    "friendly_name": ""
                },
                "c9b4c44c-0c68-447e-b64d-1bcb3fac0c73": {
                    "_id_": "c9b4c44c-0c68-447e-b64d-1bcb3fac0c73",
                    "name": "URLs",
                    "members": {
                        "0": { "address": "cradlepoint.com" }
                    },
                    "friendly_name": ""
                }
            }
        }
    },
    []
]
```

Members hold either IP addresses or hostnames, and both are copied as-is. If the
source group defines no `identities.ip`, the app says so instead of pushing
anything.

## Notes

- Destination push failures are reported per group; one failure does not abort the
  rest of the batch.
- `config.json` holds API keys in plaintext. It is gitignored and written with
  `0600` permissions on macOS/Linux.
- Group configs are validated by NCM against the firmware DTD. A `400` in the
  results table usually means the destination group's firmware does not accept the
  config as sent.
