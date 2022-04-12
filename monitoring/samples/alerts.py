"""
This file contains a sample using the functions in the utils module
to poll the alerts endpoint for all new alerts on your account.
The sample process_alert() function just prints any new alert to the console,
but you can replace it with anything you want (e.g., code to send an email
to your admin, write the alert to your database, send it to a log server)
"""

from monitoring.utils.session import APISession
from pprint import pprint
from datetime import datetime, timedelta
from monitoring.utils.timeuuid_endpoint import get_filtered, poll
from monitoring.utils.credentials import get_credentials
from monitoring.utils.logger import get_logger

POLL_INTERVAL = 600  # 10 minutes; adjust to your needs
POLL_START_TIME = datetime.utcnow() - timedelta(hours=1)


def retrieve_all_alerts(
    session=None,
    start_ts=POLL_START_TIME,
    start_uuid=None,
    router_ids=[],  # optional restriction by router
):
    """
    Calls process_alert() for all alerts in a given time range.

    :param session: APISession object. Required.
    :param start_ts: Starting timestamp for time window. Specify this or start_uuid.
    :param start_uuid: Starting timeuuid for time window.
    :param router_ids: Optional list of router_ids to restrict query.


    NOTE:  This function delegates to get_filtered().  See the comments there
    for more information about defaults and behavior.
    """
    if start_uuid:
        alerts = get_filtered(
            session=session,
            endpoint="alerts",
            after_uuid=start_uuid,
            router_ids=router_ids,
        )
    else:
        alerts = get_filtered(
            session=session,
            endpoint="alerts",
            after_time=start_ts,
            router_ids=router_ids,
        )
    for a in alerts:
        process_alert(a)


def poll_for_new_alerts(session=None, start_ts=POLL_START_TIME):
    """
    Polls for new alerts.  Calls process_alert() for all new alerts since the
    last poll.

    :param session: APISession object. Required.
    :param start_ts: Starting timestamp for polling time window.
    """
    poll(
        session=session,
        endpoint="alerts",
        sleeptime=POLL_INTERVAL,
        process_one_fn=process_alert,
        after_time=start_ts,
    )


def process_alert(a):
    """Do whatever you need to with a single alert."""
    pprint(a)


if __name__ == "__main__":
    """
    Run the alert poll
    """
    logger = get_logger()
    try:
        with APISession(**get_credentials(), logger=logger) as s:
            poll_for_new_alerts(s)
    except Exception as x:
        logger.exception("Unexpected exception")
