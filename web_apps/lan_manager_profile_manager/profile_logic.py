"""Pure Remote Connect profile logic: normalize, compare, group, plan.

Kept separate from serve.py so the matching and replace rules can be reasoned
about and checked without a server, credentials, or network.

Rules this module encodes
-------------------------
* **Matching is by name, case-insensitive.** A router "has" profile ``Foo`` if
  any of its profiles is named ``foo``/``FOO``/``Foo`` (leading/trailing
  whitespace ignored). This is what "replace, don't duplicate" keys on.
* **Pushing a profile leaves exactly one profile of that name.** If one or more
  name matches already exist, one is kept and updated in place (preferring one
  that already matches exactly, then one of the same type, oldest first), and
  the rest are deleted. A type change (e.g. SSH -> HTTPS) creates the new
  profile first and only then deletes the old one(s), so a failed create never
  leaves the router with nothing.
* **Variants compare type plus every setting.** Two profiles are the same
  variant only if their type, exact name (case included), port, and the
  type-specific fields (address / username / resolution) are all equal.
  Timestamps and IDs are ignored.
"""

import ipaddress
import json

# Short type -> type-specific fields (beyond name and port), per the v3
# remote_connect_profiles docs.
TYPE_FIELDS = {
    "ssh": ["address", "username"],
    "http": ["address"],
    "https": ["address"],
    "rdp": ["address", "username", "resolution"],
    "vnc": ["address", "username"],
    "serial": [],
}

TYPE_LABELS = {
    "ssh": "SSH", "http": "HTTP", "https": "HTTPS",
    "rdp": "RDP", "vnc": "VNC", "serial": "Serial",
}

DEFAULT_PORTS = {"ssh": 22, "http": 80, "https": 443, "rdp": 3389,
                 "vnc": 5900, "serial": 1}

# Fields that are required on create/update for each type. Optional ones may
# be blank (sent as null).
REQUIRED_FIELDS = {
    "ssh": ["address", "username"],
    "http": ["address"],
    "https": ["address"],
    "rdp": ["address", "resolution"],
    "vnc": ["address"],
    "serial": [],
}

NAME_MAX = 32
USERNAME_MAX = 64


def short_type(full_type):
    """``remote_connect_ssh_profile`` -> ``ssh``. Passes short forms through."""
    t = str(full_type or "").strip().lower()
    if t.startswith("remote_connect_"):
        t = t[len("remote_connect_"):]
    if t.endswith("_profile"):
        t = t[:-len("_profile")]
    return t


def full_type(short):
    """``ssh`` -> ``remote_connect_ssh_profile``."""
    return f"remote_connect_{short_type(short)}_profile"


def name_key(name):
    """Case-insensitive, whitespace-trimmed key used for every name match."""
    return str(name or "").strip().casefold()


def _norm_text(value):
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _norm_port(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def settings_of(stype, attrs):
    """The comparable settings for a profile: name, port, type-specific fields.

    ``attrs`` may be raw API attributes or a user-entered spec; either way the
    result has the same shape, so equality means "identical profile".
    """
    stype = short_type(stype)
    attrs = attrs or {}
    settings = {
        "name": _norm_text(attrs.get("name")),
        "port": _norm_port(attrs.get("port")),
    }
    for field in TYPE_FIELDS.get(stype, []):
        settings[field] = _norm_text(attrs.get(field))
    return settings


def fingerprint(stype, settings):
    """Stable string identity for a (type, settings) pair."""
    return json.dumps([short_type(stype), settings], sort_keys=True)


def _id_sort_key(pid):
    text = str(pid)
    return (0, int(text)) if text.isdigit() else (1, text)


def normalize_profile(raw):
    """Flatten a v3 JSON:API profile record into the shape the app uses."""
    attrs = raw.get("attributes") or {}
    rels = raw.get("relationships") or {}

    def rel(name):
        return ((rels.get(name) or {}).get("data") or {}).get("id")

    stype = short_type(raw.get("type"))
    settings = settings_of(stype, attrs)
    return {
        "id": str(raw.get("id")),
        "type": stype,
        "name": settings["name"] or "",
        "name_key": name_key(settings["name"]),
        "settings": settings,
        "fingerprint": fingerprint(stype, settings),
        "router_id": str(rel("router")) if rel("router") is not None else None,
        "account_id": str(rel("account")) if rel("account") is not None else None,
        "created_at": attrs.get("created_at"),
        "updated_at": attrs.get("updated_at"),
    }


def spec_from_profile(profile):
    """A push spec (type + settings) copied from a normalized profile."""
    return {"type": profile["type"], "settings": dict(profile["settings"])}


def spec_from_form(form):
    """Build a push spec from user input: {type, name, port, address, ...}."""
    stype = short_type(form.get("type"))
    return {"type": stype, "settings": settings_of(stype, form)}


def validate_spec(spec):
    """Return a list of human-readable problems; empty means valid."""
    problems = []
    stype = spec.get("type")
    if stype not in TYPE_FIELDS:
        return [f"Unknown profile type: {stype!r}"]
    s = spec.get("settings") or {}

    name = s.get("name")
    if not name:
        problems.append("Name is required")
    elif len(name) > NAME_MAX:
        problems.append(f"Name must be {NAME_MAX} characters or fewer "
                        f"({len(name)} given)")

    port = s.get("port")
    if port is None:
        problems.append("Port is required and must be a whole number")
    elif stype == "serial":
        if not 1 <= port <= 8:
            problems.append("Serial port must be between 1 and 8")
    elif not 1 <= port <= 65535:
        problems.append("Port must be between 1 and 65535")

    for field in REQUIRED_FIELDS[stype]:
        if not s.get(field):
            problems.append(f"{field.capitalize()} is required for "
                            f"{TYPE_LABELS[stype]} profiles")

    address = s.get("address")
    if "address" in TYPE_FIELDS[stype] and address:
        try:
            ipaddress.IPv4Address(address)
        except ValueError:
            problems.append(f"Address must be an IPv4 address ({address!r} given)")

    username = s.get("username")
    if username and len(username) > USERNAME_MAX:
        problems.append(f"Username must be {USERNAME_MAX} characters or fewer")
    return problems


def api_attributes(spec, for_update=False):
    """JSON:API ``attributes`` for a POST (create) or PUT (update).

    On create, blank optional fields are omitted. On update they are sent as
    null so a stale value on the target (e.g. an old RDP username) is cleared
    rather than silently kept — otherwise "copy the correct one over it" would
    leave a mismatch behind.
    """
    s = spec["settings"]
    attrs = {"name": s["name"], "port": s["port"]}
    for field in TYPE_FIELDS[spec["type"]]:
        value = s.get(field)
        if value is not None or for_update:
            attrs[field] = value
    return attrs


def describe_settings(stype, settings):
    """One-line human summary, e.g. ``SSH · port 22 · 10.0.0.5 · user admin``."""
    parts = [TYPE_LABELS.get(stype, stype), f"port {settings.get('port')}"]
    if settings.get("address"):
        parts.append(settings["address"])
    if settings.get("username"):
        parts.append(f"user {settings['username']}")
    if settings.get("resolution"):
        parts.append(settings["resolution"])
    return " · ".join(parts)


def plan_push(spec, existing):
    """Work out how to make one router carry exactly ``spec``.

    ``existing`` is the router's current list of normalized profiles.
    Returns ``{"outcome", "actions", "keeper_id", "matches"}`` where actions is
    an ordered list of ``("create",)``, ``("update", id)``, ``("delete", id)``.
    Creates and updates always come before deletes.

    Outcomes:
      create     — no profile of that name yet
      unchanged  — exactly one, already identical
      update     — one same-type profile updated in place
      dedupe     — identical one kept, extra same-name copies deleted
      replace    — type differs; create new, then delete old
    (update may also delete extras; the actions list is authoritative.)
    """
    key = name_key(spec["settings"]["name"])
    target_fp = fingerprint(spec["type"], spec["settings"])
    matches = sorted((p for p in existing if p["name_key"] == key),
                     key=lambda p: _id_sort_key(p["id"]))

    if not matches:
        return {"outcome": "create", "actions": [("create",)],
                "keeper_id": None, "matches": []}

    same_type = [p for p in matches if p["type"] == spec["type"]]
    if not same_type:
        actions = [("create",)] + [("delete", p["id"]) for p in matches]
        return {"outcome": "replace", "actions": actions, "keeper_id": None,
                "matches": matches}

    exact = [p for p in same_type if p["fingerprint"] == target_fp]
    keeper = exact[0] if exact else same_type[0]
    actions = []
    if not exact:
        actions.append(("update", keeper["id"]))
    actions += [("delete", p["id"]) for p in matches if p["id"] != keeper["id"]]

    if not actions:
        outcome = "unchanged"
    elif exact:
        outcome = "dedupe"
    else:
        outcome = "update"
    return {"outcome": outcome, "actions": actions, "keeper_id": keeper["id"],
            "matches": matches}


def verify_push(spec, existing):
    """True if ``existing`` holds exactly one profile of that name, identical."""
    key = name_key(spec["settings"]["name"])
    matches = [p for p in existing if p["name_key"] == key]
    return (len(matches) == 1
            and matches[0]["fingerprint"] == fingerprint(spec["type"],
                                                         spec["settings"]))


def group_variants(profiles):
    """Group profiles into variants of identical type + settings.

    Returns a list of ``{"fingerprint", "type", "settings", "summary",
    "profiles"}`` sorted largest first, so the common (usually correct) one
    leads and the outliers follow.
    """
    buckets = {}
    for p in profiles:
        bucket = buckets.setdefault(p["fingerprint"], {
            "fingerprint": p["fingerprint"],
            "type": p["type"],
            "settings": p["settings"],
            "summary": describe_settings(p["type"], p["settings"]),
            "profiles": [],
        })
        bucket["profiles"].append(p)
    variants = list(buckets.values())
    variants.sort(key=lambda v: (-len(v["profiles"]), v["summary"].lower()))
    return variants
