"""
This file contains a sample using the functions in the utils module
to poll the net_device_signal_samples endpoint for all new signal samples.
The sample process_signal_sample() function just prints any new metrics to the
console, but you can replace it with anything you want (e.g., write the info
to your database, send it to a log server)
"""
from pprint import pprint
from datetime import datetime, timedelta
from time import sleep
from monitoring.utils.session import APISession
from monitoring.utils.timeuuid_endpoint import get_filtered
from monitoring.utils.credentials import get_credentials
from monitoring.utils.logger import get_logger


POLL_INTERVAL = 3600  # 1 hour; adjust to your needs
ID_BATCH_LIMIT = 100  # we are allowed to request samples for at most 100  IDs at a time
POLL_START_TIME = datetime.utcnow() - timedelta(hours=1)


def poll_for_new_samples(session=None, ids=[]):
    endpoint = "net_device_signal_samples"

    start_ts = POLL_START_TIME
    last_uuid = None

    while True:
        batch_idx = 0

        while batch_idx < len(ids):
            batch_ids = ids[batch_idx:ID_BATCH_LIMIT]
            if not last_uuid and start_ts:
                recs = get_filtered(
                    endpoint=endpoint,
                    session=session,
                    after_time=start_ts,
                    order_by=["created_at_timeuuid"],
                    net_device_ids=batch_ids,
                )
            else:
                recs = get_filtered(
                    endpoint=endpoint,
                    session=session,
                    after_uuid=last_uuid,
                    order_by=["created_at_timeuuid"],
                    net_device_ids=batch_ids,
                )
            for r in recs:
                process_signal_sample(r)
                last_uuid = r["created_at_timeuuid"]
            batch_idx += len(batch_ids)

        sleep(POLL_INTERVAL)


def process_signal_sample(s):
    """Do whatever you need to with a single signal_sample."""
    pprint(s)


if __name__ == "__main__":
    logger = get_logger()
    try:
        with APISession(**get_credentials(), logger=logger) as s:
            # get a list of all my net device ids:
            recs = s.get(endpoint="net_devices", filter={"fields": "id"})
            ids = [rec["id"] for rec in recs]

            # poll them
            poll_for_new_samples(s, ids)
    except Exception as x:
        logger.exception("Unexpected exception")
