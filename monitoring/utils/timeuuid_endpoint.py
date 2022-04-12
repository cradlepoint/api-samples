"""
Common utility functions for the time series endpoints that use timeuuid
fields.
"""

from datetime import datetime, timedelta
from time import sleep

DEFAULT_POLL_INTERVAL = 3600  # one hour


def get_filtered(
    session=None,
    endpoint=None,
    after_rec=None,
    after_time=None,
    after_uuid=None,
    before_time=None,
    router_ids=None,
    net_device_ids=None,
    order_by=["created_at_timeuuid"],
    batchsize=500,
):
    """
    Retrieve a list of records based on a filter.

    :param session: APISession instance. Required.
    :param endpoint: Endpoint to query. Required.
    :param after_rec: Return records that were written after this record. Optional.
    :param after_time: Return records that were written after this time. Optional.
    :param after_uuid: Return records that were written after this timeuuid. Optional.
    :param before_time: Return records that were written before this time. Optional.
    :param router_ids: Return records where the router_id is in this list. Optional.
    :param net_device_ids: Return records where the net_device_id is in this list. Optional.
    :param order_by: Field to sort by
    :param batchsize: Maximum number of rows per server page.
    :return: An iterable generator that will yield all the records matching
    the filter criteria.  Note that this generator will page transparently,
    as necessary.

    NOTE: We will always default the time window to guarantee a before and
    after limit:

    If not set, before_time will default to one minute ago. This is
    because we should never ask for records that overlap "now", since records
    that come in while the query is being processed may or may not show up
    in the result set, and this can be confusing and nondeterministic,
    particularly if our goal is to poll to see all records over time.

    If no "after" is set, we will default to one day ago to start the
    time window.  Asking for records going back to the beginning of time
    doesn't make sense, since endpoints store limited time windows.

    See
    https://cradlepoint.com/blog/marc-jourdenais/time-management-netcloud-api-0
    for more information of choosing time windows.

    """
    # add the time window for the query
    if after_time:
        filter = {"created_at__gt": after_time.isoformat()}
    elif after_rec:
        filter = {"created_at_timeuuid__gt": after_rec["created_at_timeuuid"]}
    elif after_uuid:
        filter = {"created_at_timeuuid__gt": after_uuid}
    else:
        after_time = datetime.utcnow() - timedelta(days=1)
        filter = {"created_at__gt": after_time.isoformat()}

    if not before_time:
        before_time = datetime.utcnow() - timedelta(minutes=1)
    filter["created_at__lt"] = before_time.isoformat()

    # apply filter for router IDs if present
    if router_ids:
        filter["router__in"] = ",".join(router_ids)

    # apply filter for net device IDs if present
    if net_device_ids:
        filter["net_device__in"] = ",".join(net_device_ids)

    # now that we've constructed our filter, do the actual fetching
    return session.get(
        endpoint=endpoint, filter=filter, order_by=order_by, batchsize=batchsize
    )


def get_one(session=None, endpoint=None, timeuuid=None):
    """
    Retrieve a single record matching the arguments.

    :param session: APISession instance. Required.
    :param endpoint: Endpoint to query. Required.
    :param timeuuid: Timeuuid to match. Required

    :return: one record matching the arguments or None, if not found
    """
    filter = {"created_at_timeuuid": timeuuid}
    alerts = list(session.get(endpoint=endpoint, filter=filter))
    if alerts:
        return alerts[0]
    else:
        return None


def poll(
    session=None,
    endpoint=None,
    after_time=None,
    after_uuid=None,
    sleeptime=DEFAULT_POLL_INTERVAL,
    process_one_fn=None,
    router_ids=None,
    net_device_ids=None,
):
    """
    Poll the server to return new records from the designated endpoint.

    The poll loop stores the most recent timeuuid from the prior poll to
    filter the next poll.  The poll will only report new records a minute
    after they appear.  See the discussion for "before_time" in
    get_filtered() to understand why.

    :param session: APISession instance. Required.
    :param endpoint: Endpoint to query. Required.
    :param after_time: Start poll for records after this time.  Optional.
    :param after_uuid: Start poll for records after this uuid. Optional.
    :param sleeptime: time to sleep between polls in seconds. Optional.
    :param process_one_fn: function to execute when a new record is found.
    :param router_ids: Return records where the router_id is in this list. Optional.
    :param net_device_ids: Return records where the net_device_id is in this list. Optional.

    Note: this function mostly delegates to get_filtered() in a loop, so see
    get_filtered()
    for more information about how arguments are handled.
    """
    if not process_one_fn:
        return

    last_uuid = after_uuid

    while True:
        if not last_uuid and after_time:
            recs = get_filtered(
                endpoint=endpoint,
                session=session,
                after_time=after_time,
                order_by=["created_at_timeuuid"],
                router_ids=router_ids,
                net_device_ids=net_device_ids,
            )
        else:
            recs = get_filtered(
                endpoint=endpoint,
                session=session,
                after_uuid=last_uuid,
                order_by=["created_at_timeuuid"],
                router_ids=router_ids,
                net_device_ids=net_device_ids,
            )
        for r in recs:
            process_one_fn(r)
            last_uuid = r["created_at_timeuuid"]
        sleep(sleeptime)
