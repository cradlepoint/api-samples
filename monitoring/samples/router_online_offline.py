"""
This file contains a sample using the functions in the utils module
to poll the routers endpoint for all router state (online/offline/initialized)
changes on your account.

The sample process_state_change() function just prints any state changes to the
console, but you can replace it with anything you want (e.g., write the info
 to your database, send it to a log server, send an email)
"""
from pprint import pprint
from time import sleep
from monitoring.utils.session import APISession
from monitoring.utils.credentials import get_credentials
from monitoring.utils.logger import get_logger

POLL_INTERVAL = 600  # 10 minutes; adjust to your needs


def get_max_ts(ts1, ts2):
    """Determine max of two timestamps, allowing for nulls."""
    if ts1 and ts2:
        return max(ts1, ts2)
    elif ts1:
        return ts1
    else:
        return ts2


def poll_for_state_changes(session=None):
    """Poll for state changes, starting now."""
    prior_state = {}
    last_ts = None

    # first get current/prior state for all routers, so we can report
    # it as part of the info when the state changes.
    recs = session.get(
        endpoint="routers", filter={"fields": "id,state,state_updated_at"}
    )
    for rec in recs:
        prior_state[rec["id"]] = rec["state"]
        last_ts = get_max_ts(last_ts, rec["state_updated_at"])

    # Now poll for any changes since the last one. Note that we will only
    # retrieve records from the server where the state has changed, so
    # we don't have to do any processing on unchanged records. We also
    # only retrieve the fields we need to save bandwidth/response time.
    while True:
        recs = session.get(
            endpoint="routers",
            filter={
                "state_updated_at__gt": last_ts,
                "fields": "id,state,state_updated_at",
            },
        )

        for rec in recs:
            info = {
                "router_id": rec["id"],
                "state": rec["state"],
                "state_updated_at": rec["state_updated_at"],
                "prior_state": prior_state.get(rec["id"], "unknown"),
            }
            process_state_change(info)
            prior_state[rec["id"]] = rec["state"]
            last_ts = get_max_ts(last_ts, rec["state_updated_at"])

        sleep(POLL_INTERVAL)


def process_state_change(change):
    """Do whatever you need to with a state change."""
    pprint(change)


if __name__ == "__main__":
    logger = get_logger()
    try:
        with APISession(
            **get_credentials(),
            logger=logger,
        ) as s:
            poll_for_state_changes(s)
    except Exception as x:
        logger.exception("Unexpected exception")
