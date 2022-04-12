"""
This file contains a sample using the functions in the utils module
to poll the net_device_metrics endpoint for all metrics changes on your account.
The sample process_metrics_change() function just prints any new metrics to the
console, but you can replace it with anything you want (e.g., write the info
 to your database, send it to a log server)
"""
from pprint import pprint
from time import sleep
from datetime import datetime, timedelta, timezone
from dateutil import parser
from monitoring.utils.session import APISession
from monitoring.utils.credentials import get_credentials
from monitoring.utils.logger import get_logger

POLL_INTERVAL = 600  # 10 minutes; adjust to your needs
POLL_START_TIME = datetime.utcnow().replace(tzinfo=timezone.utc) - timedelta(hours=1)


def get_max_ts(ts1, ts2):
    """Determine max of two timestamps, allowing for nulls."""
    if ts1 and ts2:
        return max(ts1, ts2)
    elif ts1:
        return ts1
    else:
        return ts2


def poll_for_metrics_changes(session=None):

    # Poll for any changes since the last one. Note that we will only
    # retrieve records from the server where the state has changed, so
    # we don't have to do any processing on unchanged records.
    last_ts = POLL_START_TIME
    while True:
        recs = session.get(
            endpoint="net_device_metrics", filter={"update_ts__gt": last_ts}
        )
        for rec in recs:
            process_metrics_change(rec)
            last_ts = get_max_ts(last_ts, parser.isoparse(rec["update_ts"]))

        sleep(POLL_INTERVAL)


def process_metrics_change(change):
    """Do whatever you need to with a state change."""
    pprint(change)


if __name__ == "__main__":
    logger = get_logger()
    try:
        with APISession(**get_credentials(), logger=logger) as s:
            start_ts = POLL_START_TIME
            poll_for_metrics_changes(session=s)
    except Exception as x:
        logger.exception("Unexpected exception")
