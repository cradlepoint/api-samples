# NCM API v2 Full Endpoint Reference

Auto-generated from Swagger specs and live API responses.

Generated: 2026-06-06 13:01:14 UTC

Base URL: `https://www.cradlepointecm.com/api/v2/`

---

## accounts

```
GET /api/v2/accounts/
```

### Query Parameters

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `account` | in: int<br />out: url | False | Parent account of an account/subaccount |
| `account__in` | in: int<br />out: url | False | Filter for account contains - a comma-separated list of account IDs |
| `id` | int | False | Object ID of an accounts record |
| `id__in` | int | False | Filter for ID contains - a comma-separated list of account record IDs |
| `name` | string | False | Name of the account |
| `name__in` | string | False | Filter for name contains - a comma-separated list of account names. |
| `expand` | string | False | Specifies that the returned value for the passed in attribute be expanded in the response body. |
| `limit` | int | False | Restricts the number of records returned in a recordset to this value. Max value is 500. |
| `offset` | int | False | Specifies where (an index) in a recordset to begin returning records. |

### Response Fields

| Field | Type | Sample Value |
|-------|------|--------------|
| `account` | str | https://www.us0.cradlepointecm.com/api/v2/accounts/3644/ |
| `id` | str | 157 |
| `is_disabled` | bool | False |
| `name` | str | timlay account |
| `resource_url` | str | https://www.us0.cradlepointecm.com/api/v2/accounts/157/ |

---

## activity_logs

```
GET /api/v2/activity_logs/
```

### Query Parameters

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `account` | int | False | The ID of your account |
| `created_at__exact` | datetime | False | The exact date/time when the activity log event was created |
| `created_at__lt` | datetime | False | Less than date/time filtering operator for when the activity log event was created |
| `created_at__lte` | datetime | False | Less than or equal date/time filtering operator for when the activity log event was created |
| `created_at__gt` | datetime | False | Greater than date/time filtering operator for when the activity log event was created |
| `created_at__gte` | datetime | False | Greater than or equal date/time filtering operator for when the activity log event was created |
| `action__timestamp__exact` | datetime | False | The exact date/time when the action occurred |
| `action__timestamp__lt` | datetime | False | Less than date/time filtering operator for when action occurred |
| `action__timestamp__lte` | datetime | False | Less than or equal date/time filtering operator for when action occurred |
| `action__timestamp__gt` | datetime | False | Greater than date/time filtering operator for when action occurred |
| `action__timestamp__gte` | datetime | False | Greater than or equal date/time filtering operator for when action occurred |
| `actor__id` | string | False | The user ID of the actor who took the action |
| `object__id` | string | False | The exact ID of the object for the activity |
| `action__id__exact` | string | False | The exact ID of the action of the activity |
| `actor__type` | string | False | Type of actor who took the action |
| `action__type` | string | False | Type of action taken |
| `object__type` | string | False | Type of object the action was taken upon |
| `limit` | int | False | Restricts the number of records returned in a recordset to this value. Max value is 500. |
| `offset` | int | False | Specifies where (an index) in a recordset to begin returning records. |

### Response Fields

| Field | Type | Sample Value |
|-------|------|--------------|
| `action` | dict | {'diff': {'target_config': '[{"system": {"asset_id": "DL: 18... |
| `actor` | dict | {'id': '1850632', 'mac': '00:30:44:4E:3A:E3', 'name': 'E3000... |
| `object` | dict | {'id': '1850632', 'mac': '00:30:44:4E:3A:E3', 'name': 'E3000... |

---

## alerts

```
GET /api/v2/alerts/
```

### Query Parameters

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `account` | in: int<br />out: url | False | Account this alert is related to, or null if the router field has a value |
| `created_at` | timestamp | False | Time the alert record was created in NCM |
| `created_at_timeuuid` | timeuuid | False | A unique ID associated with the created_at timestamp. Ordering by the ID is equivalent to time ordering. This field can identify a specific record or be used for paging. |
| `detected_at` | timestamp | False | Time the alert was detected |
| `friendly_info` | string | False | Human-readable description of the alert |
| `router` | in: int<br />out: url | False | Device this alert is related to, or null if the account field has a value |
| `type` | string | False | Specifies the type of the alert |
| `limit` | int | False | Restricts the number of records returned in a recordset to this value. Max value is 500. |
| `offset` | int | False | Specifies where (an index) in a recordset to begin returning records. |

### Response Fields

| Field | Type | Sample Value |
|-------|------|--------------|
| `account` | null | null |
| `created_at` | str | 2026-06-06T12:59:12.462000+00:00 |
| `created_at_timeuuid` | str | 83d52c38-61a7-11f1-a2f3-922705407062 |
| `detected_at` | str | 2026-06-06T12:59:11+00:00 |
| `friendly_info` | str | IPsec Tunnel "vti" has gone down. |
| `info` | dict | {'time': ['2026-06-06 12:59:11', 'UTC'], 'tunname': 'vti', '... |
| `router` | str | https://www.us0.cradlepointecm.com/api/v2/routers/4618577/ |
| `type` | str | ipsec_tunnel_down |

---

## alert_rules

```
GET /api/v2/alert_rules/
```

### Query Parameters

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `alert_config_id` | timeuuid | False | Unique ID of an Alert Rule |
| `account` | url | False | Parent account |
| `schedule` | string | False | Schedule for sending notifications |
| `associated_accounts` | int | False | A list of account-identfier ints |
| `associated_groups` | int | False | A list of group-identfier ints |
| `filter_criteria` | json | False | Alert types to add to the Alert Rule |
| `email_destinations` | int | False | Email dests (list of ints) used for email notifications |
| `http_destinations` | timeuuid | False | HTTP dests (list of timeuuids) for push notifications |
| `updated_at` | timestamp | False | Last time an Alert Rule was modified |
| `settings` | json | False | Additional settings for PDP service-overage alerts |
| `limit` | int | False | Restricts the number of records returned in a recordset to this value. Max value is 500. |

### Response Fields

| Field | Type | Sample Value |
|-------|------|--------------|
| `account` | str | https://www.us0.cradlepointecm.com/api/v2/accounts/27748/ |
| `alert_config_id` | str | 34420a7e-5bb2-11f1-9175-2ef2c4f6c013 |
| `associated_accounts` | list | [] |
| `associated_groups` | list | [613379, 617420] |
| `email_destinations` | list | [] |
| `external_rules` | null | null |
| `filter_criteria` | dict | {'alert_type__in': ['wwan_connected', 'wwan_standby', 'wwan_... |
| `http_destinations` | list | [] |
| `last_summary_ts` | str | 2026-05-29T23:00:36.424544+00:00 |
| `schedule` | null | null |
| `settings` | dict | {'intel_reboot_status_change': {'reason': ['NCOS Upgrade']}} |
| `updated_at` | str | 2026-05-29T23:00:36.421507+00:00 |

---

## alert_push_destinations

```
GET /api/v2/alert_push_destinations/
```

### Query Parameters

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `destination_config_id` | timeuuid | False | Unique ID of an Alert Push Destination |
| `limit` | int | False | Restricts the number of records returned in a recordset to this value. Max value is 500. |

### Response Fields

| Field | Type | Sample Value |
|-------|------|--------------|
| `account` | str | https://www.us0.cradlepointecm.com/api/v2/accounts/105524/ |
| `authentication` | dict | {'secret': '*'} |
| `destination_config_id` | str | a6dc8d34-1410-11f1-851a-263675be6084 |
| `enabled` | bool | True |
| `endpoint` | dict | {'url': 'https://eox714chfkbizl.m.pipedream.net'} |
| `last_error_at` | str | 2026-02-28T09:19:27.184909Z |
| `last_error_text` | str | 400 Bad Request |
| `name` | str | PipeDream 2 |
| `suspended` | bool | True |
| `updated_at` | str | 2026-03-27T00:15:48.008667Z |

---

## batteries

```
GET /api/v2/batteries/
```

### Query Parameters

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `router` | int | True | ID of E100-series router to query for battery information |
| `limit` | int | False | Restricts the number of records returned in a recordset to this value. Max value is 500. |
| `offset` | int | False | Specifies where (an index) in a recordset to begin returning records. |

### Response Fields

| Field | Type | Sample Value |
|-------|------|--------------|
| `created_at` | str | 2025-08-05T19:20:38.073099+00:00 |
| `health` | int | 100 |
| `id` | str | 604938 |
| `manufacturer` | str | GETAC |
| `milliamps` | int | 618 |
| `millivolts` | int | 6864 |
| `resource_url` | str | https://www.us0.cradlepointecm.com/api/v2/batteries/604938/ |
| `router` | str | https://www.us0.cradlepointecm.com/api/v2/routers/3747186/ |
| `rsoc` | int | 12 |
| `serial` | str | GA2038BA000210 |
| `status` | str | Charging |
| `temp` | int | 37 |
| `time_remaining` | int | 630 |
| `type` | str | battery |
| `updated_at` | str | 2025-10-03T05:52:50.699042+00:00 |

---

## configuration_managers

```
GET /api/v2/configuration_managers/
```

### Query Parameters

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `account` | in: int<br />out: url | False | Account that contains the configuration_managers record |
| `account__in` | in: int<br />out: url | False | Filter for account contains - a comma-separated list of account IDs |
| `id` | int | False | ID of a configuration_managers record |
| `id__in` | int | False | Filter for ID contains - a comma-separated list of configuration_managers record IDs |
| `router` | in: int<br />out: url | False | Router ID |
| `router__in` | in: int<br />out: url | False | Filter for router ID contains - a comma-separated list of router-record IDs |
| `synched` | boolean | False | True if device configuration is synced |
| `suspended` | boolean | False | True if device configuration sync is paused |
| `expand` | string | False | Specifies that the returned value for the passed in attribute be expanded in the response body |
| `limit` | int | False | Restricts the number of records returned in a recordset to this value. Max value is 500. |
| `offset` | int | False | Specifies where (an index) in a recordset to begin returning records. |

### Response Fields

| Field | Type | Sample Value |
|-------|------|--------------|
| `account` | str | https://www.us0.cradlepointecm.com/api/v2/accounts/None/ |
| `actual` | list | [{}, []] |
| `configuration` | list | [{}, []] |
| `id` | str |  |
| `pending` | list | [{}, []] |
| `resource_url` | str | https://www.us0.cradlepointecm.com/api/v2/configuration_mana... |
| `router` | str | https://www.us0.cradlepointecm.com/api/v2/routers/None/ |
| `suspended` | bool | False |
| `synched` | bool | True |
| `target` | null | null |
| `version_number` | int | 0 |

---

## device_apps

```
GET /api/v2/device_apps/
```

### Query Parameters

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `account` | in: int<br />out: url | False | Account that owns the device_apps object |
| `account__in` | in: int<br />out: url | False | Filter for account contains - a comma-separated list of account record IDs |
| `name` | string | False | Name of the device app |
| `name__in` | string | False | Filter for name contains - a comma-separated list of device app names |
| `id` | int | False | device_apps record object ID |
| `id__in` | int | False | Filter for device_apps ID contains - a comma-separated list of device_apps record IDs |
| `uuid` | int | False | Object UUID |
| `uuid__in` | int | False | Filter for uuid contains - a comma-separated list of uuids |
| `expand` | string | False | Specifies that the returned value for the passed in attribute be expanded in the response body. |
| `limit` | int | False | Restricts the number of records returned in a recordset to this value. Max value is 500. |
| `offset` | int | False | Specifies where (an index) in a recordset to begin returning records. |

### Response Fields

| Field | Type | Sample Value |
|-------|------|--------------|
| `account` | str | https://www.us0.cradlepointecm.com/api/v2/accounts/22746/ |
| `created_at` | str | 2018-07-10T20:52:38.733636+00:00 |
| `description` | str | A Driver for Monnit Gateways and Sensors |
| `id` | str | 37 |
| `name` | str | monnit_driver_UI |
| `resource_url` | str | https://www.us0.cradlepointecm.com/api/v2/device_apps/37/ |
| `updated_at` | str | 2018-07-10T20:52:38.738727+00:00 |
| `uuid` | str | 29d26837-4013-4f29-8d54-5c27dfc7be3e |

---

## device_app_bindings

```
GET /api/v2/device_app_bindings/
```

### Query Parameters

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `account` | in: int<br />out: url | False | Account that owns the object |
| `account__in` | in: int<br />out: url | False | Filter for account contains - a comma-separated list of account IDs |
| `group` | in: int<br />out: url | False | Group that owns the object |
| `group__in` | in: int<br />out: url | False | Filter for group contains - a comma-separated list of group IDs |
| `app_version` | in: int<br />out: url | False | Device app version |
| `app_version__in` | in: int<br />out: url | False | Filter for app_version contains - a comma-separated list of app version IDs |
| `id` | int | False | ID of the device_app_bindings record |
| `id__in` | int | False | Filter for ID contains - a comma-separated list of account IDs |
| `state` | string | False | Object state |
| `state__in` | string | False | Filter for states contains - a comma-separated list of states |
| `expand` | string | False | Specifies that the returned value for the passed in attribute be expanded in the response body |
| `limit` | int | False | Restricts the number of records returned in a recordset to this value. Max value is 500. |
| `offset` | int | False | Specifies where (an index) in a recordset to begin returning records. |

### Response Fields

| Field | Type | Sample Value |
|-------|------|--------------|
| `account` | str | https://www.us0.cradlepointecm.com/api/v2/accounts/27449/ |
| `app_version` | str | https://www.us0.cradlepointecm.com/api/v2/device_app_version... |
| `created_at` | str | 2017-09-28T17:29:00.865792+00:00 |
| `group` | str | https://www.us0.cradlepointecm.com/api/v2/groups/65543/ |
| `id` | str | 6 |
| `resource_url` | str | https://www.us0.cradlepointecm.com/api/v2/device_app_binding... |
| `state` | str |  |
| `updated_at` | str | 2017-09-28T17:29:00.865827+00:00 |

---

## device_app_states

```
GET /api/v2/device_app_states/
```

### Query Parameters

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `account` | in: int<br />out: url | False | Account that owns the device_app_states object |
| `account__in` | in: int<br />out: url | False | Filter for account contains - a comma-separated list of account record IDs |
| `router` | in: int<br />out: url | False | Router where the Device App is installed |
| `router__in` | in: int<br />out: url | False | Filter for router ID contains - a comma-separated list of router record IDs |
| `app_version` | in: int<br />out: url | False | The version ID of the associated device_app_versions |
| `app_version__in` | in: int<br />out: url | False | Filter for app_version contains - a comma-separated list of associated device_app_versions version IDs |
| `id` | int | False | device_app_states record object ID |
| `id__in` | int | False | Filter for device_app_states ID contains - a comma-separated list of device_app_states record IDs |
| `state` | string | False | device_app_states object state |
| `state__in` | string | False | Filter for device_app_states state contains - a comma-separated list of state record states |
| `expand` | string | False | Specifies that the returned value for the passed in attribute be expanded in the response body |
| `limit` | int | False | Restricts the number of records returned in a recordset to this value. Max value is 500. |
| `offset` | int | False | Specifies where (an index) in a recordset to begin returning records. |

### Response Fields

| Field | Type | Sample Value |
|-------|------|--------------|
| `account` | str | https://www.us0.cradlepointecm.com/api/v2/accounts/3644/ |
| `app_version` | str | https://www.us0.cradlepointecm.com/api/v2/device_app_version... |
| `created_at` | str | 2024-07-12T21:10:20.023337+00:00 |
| `id` | str | 326838856 |
| `resource_url` | str | https://www.us0.cradlepointecm.com/api/v2/device_app_states/... |
| `router` | str | https://www.us0.cradlepointecm.com/api/v2/routers/4447736/ |
| `state` | str | offline |
| `updated_at` | str | 2024-11-01T05:11:05.638982+00:00 |

---

## device_app_versions

```
GET /api/v2/device_app_versions/
```

### Query Parameters

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `account` | in: int<br />out: url | False | Account that owns the Device App Versions object |
| `account__in` | in: int<br />out: url | False | Filter for account ID contains - a comma-separated list of account record IDs |
| `app` | in: int<br />out: url | False | Associated device_apps object |
| `app__in` | in: int<br />out: url | False | Filter for app contains - a comma-separated list of device_apps record IDs |
| `id` | int | False | ID of a device_app_versions record |
| `id__in` | int | False | Filter for device_app_versions ID contains - a comma-separated list of Device App Versions record IDs |
| `state` | string | False | State of a device_app_versions object (Ready, Started, Stopped) |
| `state__in` | string | False | Filter for state contains - a comma-separated list of states (see the state field above for state values) |
| `expand` | string | False | Specifies that the returned value for the passed in attribute be expanded in the response body. |
| `limit` | int | False | Restricts the number of records returned in a recordset to this value. Max value is 500. |
| `offset` | int | False | Specifies where (an index) in a recordset to begin returning records. |

### Response Fields

| Field | Type | Sample Value |
|-------|------|--------------|
| `account` | str | https://www.us0.cradlepointecm.com/api/v2/accounts/27449/ |
| `app` | str | https://www.us0.cradlepointecm.com/api/v2/device_apps/83/ |
| `created_at` | str | 2017-09-28T17:26:31.027189+00:00 |
| `id` | str | 20 |
| `resource_url` | str | https://www.us0.cradlepointecm.com/api/v2/device_app_version... |
| `state` | str | ready |
| `state_details` | str |  |
| `updated_at` | str | 2017-09-28T17:26:31.581145+00:00 |
| `version` | str | 2.0.0 |

---

## failovers

```
GET /api/v2/failovers/
```

### Query Parameters

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `account_id` | int | False | The ID of an account to view failover events |
| `group_id` | int | False | The ID of a group to view failover events |
| `router_id` | int | False | The ID of a router to view failover events |
| `started_at` | datetime | False | Started-at datetime filter for failover event |
| `ended_at` | datetime | False | Ended-at datetime filter for failover event |
| `limit` | int | False | Restricts the number of failovers records returned to this value |
| `offset` | int | False | Specifies where (the index of) in a failovers recordset to begin returning failovers records |

### Response Fields

| Field | Type | Sample Value |
|-------|------|--------------|
| `account_id` | int | 89321 |
| `carrier_name` | str | Verizon |
| `current_wan_interface` | str | mdm-31a69cd6 |
| `current_wan_priority` | float | 1.500394692 |
| `data_usage` | null | null |
| `elapsed_time` | null | null |
| `ended_at` | null | null |
| `group_id` | int | 591992 |
| `group_name` | str | E3000_OSPF_Test |
| `percent_data_cap` | null | null |
| `previous_wan_interface` | str | wwan-40:47:5e:e4:8f:66:2_4G-1 |
| `previous_wan_priority` | float | 1.2514131505 |
| `router_id` | int | 4512940 |
| `router_name` | str | E3000-d70 |
| `started_at` | str | 2026-03-11T05:26:43.513005Z |
| `tenant_id` | str | 0015000000QC88O |
| `updated_at` | str | 2026-03-11T05:27:39.047453Z |
| `uuid` | str | 0af477ba-40da-43a0-98b0-686e9357073f |

---

## firmwares

```
GET /api/v2/firmwares/
```

### Query Parameters

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `id` | int | False | The ID of a firmwares record |
| `id__in` | int | False | Filter for ID contains - a comma-separated list of firmwares record IDs |
| `version` | string | False | Version of this firmware |
| `version__in` | string | False | Filter for version contains - a comma-separated list of versions |
| `limit` | int | False | Restricts the number of records returned in a recordset to this value. Max value is 500. |
| `offset` | int | False | Specifies where (an index) in a recordset to begin returning records. |

### Response Fields

| Field | Type | Sample Value |
|-------|------|--------------|
| `built_at` | str | 2013-07-02T17:08:47+00:00 |
| `default_configuration` | str | https://www.us0.cradlepointecm.com/api/v2/firmwares/1/defaul... |
| `expires_at` | str | 2020-01-01T00:00:00+00:00 |
| `hash` | str | 25e8477e202e16dc64303c02bdc990d4d06a5daa |
| `id` | str | 1 |
| `is_deprecated` | bool | False |
| `product` | str | https://www.us0.cradlepointecm.com/api/v2/products/4/ |
| `released_at` | str | 2013-07-02T17:08:47+00:00 |
| `resource_url` | str | https://www.us0.cradlepointecm.com/api/v2/firmwares/1/ |
| `uploaded_at` | str | 2013-07-03T17:59:24.167915+00:00 |
| `url` | str | /CBR450-2013-07-02T17%3A08%3A47.bin |
| `version` | str | 4.3.2 |

---

## groups

```
GET /api/v2/groups/
```

### Query Parameters

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `account` | in: int<br />out: url | False | Account that contains the groups record |
| `account__in` | in: int<br />out: url | False | Filter for account contains - a comma-separated list of account IDs |
| `id` | int | False | ID of a groups record |
| `id__in` | int | False | Filter for ID contains - a comma-separated list of groups record IDs |
| `name` | string | False | Name of the group |
| `name__in` | string | False | Filter for names contains - a comma-separated list of group names |
| `expand` | string | False | Specifies that the returned value for the passed in attribute be expanded in the response body |
| `id__gt` | integer | False | Filter results to items with ID greater than specified value (cursor pagination) |
| `id__gte` | integer | False | Filter results to items with ID greater than or equal to specified value |
| `id__lt` | integer | False | Filter results to items with ID less than specified value |
| `id__lte` | integer | False | Filter results to items with ID less than or equal to specified value |
| `limit` | int | False | Restricts the number of records returned in a recordset to this value. Max value is 500. |
| `offset` | int | False | Specifies where (an index) in a recordset to begin returning records. |

### Response Fields

| Field | Type | Sample Value |
|-------|------|--------------|
| `account` | str | https://www.us0.cradlepointecm.com/api/v2/accounts/334/ |
| `configuration` | list | [{'dns': {'force_redir': True}, 'ethernet': {'1': {'gid': 'p... |
| `device_type` | str | router |
| `id` | str | 16125 |
| `name` | str | AER2100 Std Conf with IPS/IDS Final Config - Backup |
| `product` | str | https://www.us0.cradlepointecm.com/api/v2/products/11/ |
| `resource_url` | str | https://www.us0.cradlepointecm.com/api/v2/groups/16125/ |
| `target_firmware` | str | https://www.us0.cradlepointecm.com/api/v2/firmwares/135/ |

---

## historical_locations

```
GET /api/v2/historical_locations/
```

### Query Parameters

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `router` | int | True | The ID of the router that sent the location data. This parameter is REQUIRED. Only one router ID may be specified per query; you can't provide a list of router IDs to this endpoint. |
| `created_at__gt` | ISO datetime | False | Return only data points with created_at timestamps AFTER this datetime. If no timezone is specified, UTC is assumed. |
| `created_at_timeuuid__gt` | UUID | False | Return only data points with created_at_timeuuid values AFTER this UUID. Using this query parameter causes the query to skip older data points which were recorded before the created_at_timeuuid field was added. A unique ID associated with the created_at timestamp |
| `created_at__lte` | ISO datetime | False | Return only data points with created_at timestamps ON OR BEFORE this. If limit is reached first then this parameter does not apply. |
| `limit` | int | False | Return no more than this many location data points. If created_at__lte is reached first then this parameter does not apply. |
| `limit` | int | False | Restricts the number of records returned in a recordset to this value. Max value is 500. |
| `offset` | int | False | Specifies where (an index) in a recordset to begin returning records. |

---

## locations

```
GET /api/v2/locations/
```

### Query Parameters

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `id` | int | False | ID of a locations record |
| `id__in` | int | False | Filter for ID contains - a comma-separated list of locations record IDs |
| `limit` | int | False | Restricts the number of records returned in a recordset to this value. Max value is 500. |
| `offset` | int | False | Specifies where (an index) in a recordset to begin returning records. |

### Response Fields

| Field | Type | Sample Value |
|-------|------|--------------|
| `account` | str | https://www.us0.cradlepointecm.com/api/v2/accounts/6972/ |
| `accuracy` | int | 0 |
| `altitude_meters` | null | null |
| `id` | str | 223095 |
| `latitude` | float | 17.496755 |
| `longitude` | float | 78.366732 |
| `method` | str | manual |
| `resource_url` | str | https://www.us0.cradlepointecm.com/api/v2/locations/223095/ |
| `router` | str | https://www.us0.cradlepointecm.com/api/v2/routers/1809766/ |
| `updated_at` | str | 2026-03-29T02:45:29.163359Z |

---

## net_devices

```
GET /api/v2/net_devices/
```

### Query Parameters

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `account` | in: int<br />out: url | False | Account that owns the net_devices record |
| `account__in` | in: int<br />out: url | False | Filter for account contains - a comma-separated list of account IDs |
| `connection_state` | string | False | Connection state of a net device |
| `connection_state__in` | string | False | Filter for connection_state contains - a comma-separated list of connection states |
| `id` | int | False | ID of the net_devices record |
| `id__in` | int | False | Filter for ID contains - a comma-separated list of net_devices IDs. |
| `id__gt` | integer | False | Filter results to items with ID greater than specified value (cursor pagination) |
| `id__gte` | integer | False | Filter results to items with ID greater than or equal to specified value |
| `id__lt` | integer | False | Filter results to items with ID less than specified value |
| `id__lte` | integer | False | Filter results to items with ID less than or equal to specified value |
| `is_asset` | boolean | False | True for modem network devices |
| `ipv4_address` | string | False | Device's IPv4 address |
| `ipv4_address__in` | string | False | Filter for ipv4_address contains - a comma-separated list of ipv4 addresses |
| `mode` | string | False | Network device's mode, either WAN or LAN |
| `mode__in` | string | False | Filter for mode contains - a comma-separated list of modes |
| `router` | in: int<br />out: url | False | Cradlepoint device the network device is currently connected |
| `router__in` | in: int<br />out: url | False | Filter for router contains - a comma-separated list of router IDs |
| `expand` | string | False | Specifies that the returned value for the passed in attribute be expanded in the response body |
| `limit` | int | False | Restricts the number of records returned in a recordset to this value. Max value is 500. |
| `offset` | int | False | Specifies where (an index) in a recordset to begin returning records. |

### Response Fields

| Field | Type | Sample Value |
|-------|------|--------------|
| `account` | str | https://www.us0.cradlepointecm.com/api/v2/accounts/307/ |
| `apn` | null | null |
| `bsid` | null | null |
| `carrier` | str | Unknown Service |
| `carrier_id` | null | null |
| `channel` | null | null |
| `connection_state` | str | disconnected |
| `dns0` | null | null |
| `dns1` | null | null |
| `esn` | null | null |
| `gateway` | null | null |
| `gsn` | str | 353547060031195 |
| `homecarrid` | null | null |
| `hostname` | str | Desk850 |
| `iccid` | null | null |
| `id` | str | 1962784 |
| `imei` | str | 353547060031195 |
| `imsi` | null | null |
| `ipv4_address` | null | null |
| `ipv6_address` | null | null |
| `is_asset` | bool | True |
| `is_gps_supported` | bool | True |
| `is_upgrade_available` | bool | False |
| `is_upgrade_supported` | bool | True |
| `ltebandwidth` | null | null |
| `mac` | null | null |
| `manufacturer` | str | Cradlepoint Inc. |
| `mdn` | null | null |
| `meid` | str | 35354706003119 |
| `mfg_model` | str | MC7354-CP |
| `mfg_product` | str | MC400LPE (SIM2) |
| `mn_ha_spi` | null | null |
| `mn_ha_ss` | null | null |
| `mode` | str | wan |
| `model` | str | MC400LPE-GN (SIM2) |
| `modem_fw` | str | Generic |
| `mtu` | int | 1428 |
| `nai` | null | null |
| `name` | str | mdm-2228b51a |
| `netmask` | null | null |
| `pin_status` | str | NOSIM |
| `port` | str | modem1 |
| `prlv` | null | null |
| `profile` | null | null |
| `resource_url` | str | https://www.us0.cradlepointecm.com/api/v2/net_devices/196278... |
| `rfband` | null | null |
| `rfband5g` | null | null |
| `rfchannel` | null | null |
| `roam` | null | null |
| `router` | str | https://www.us0.cradlepointecm.com/api/v2/routers/371193/ |
| `rxchannel` | null | null |
| `serial` | str | 353547060031195 |
| `service_type` | str | Not Available |
| `ssid` | null | null |
| `summary` | str | disconnected |
| `txchannel` | null | null |
| `type` | str | mdm |
| `uid` | str | 2228b51a |
| `updated_at` | str | 2018-05-07T18:43:51.392140+00:00 |
| `uptime` | null | null |
| `ver_pkg` | str | 05.05.58.00_GENNA-UMTS,005.025_002 |
| `version` | str | 05.05.58.00_GENNA-UMTS,005.025_002 |
| `wimax_realm` | str | sprintpcs.com |

---

## net_device_health

```
GET /api/v2/net_device_health/
```

### Query Parameters

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `net_device` | int | False | ID of a net device |
| `id__gt` | integer | False | Filter results to items with ID greater than specified value (cursor pagination) |
| `id__gte` | integer | False | Filter results to items with ID greater than or equal to specified value |
| `id__lt` | integer | False | Filter results to items with ID less than specified value |
| `id__lte` | integer | False | Filter results to items with ID less than or equal to specified value |
| `limit` | int | False | Restricts the number of records returned in a recordset to this value. Max value is 500. |
| `offset` | int | False | Specifies where (an index) in a recordset to begin returning records. |

### Response Fields

| Field | Type | Sample Value |
|-------|------|--------------|
| `cellular_health_category` | str | poor |
| `cellular_health_score` | int | 0 |
| `id` | str | 25553576 |
| `net_device` | str | https://www.us0.cradlepointecm.com/api/v2/net_devices/674686... |
| `resource_url` | str | https://www.us0.cradlepointecm.com/api/v2/net_device_health/... |

---

## net_device_metrics

```
GET /api/v2/net_device_metrics/
```

### Query Parameters

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `net_device` | in: int<br />out: url | False | The unque URL for each net device in the system |
| `net_device__in` | in: int<br />out: url | False | Filter for net_device contains - a comma separated list of net device IDs |
| `id__gt` | integer | False | Filter results to items with ID greater than specified value (cursor pagination) |
| `id__gte` | integer | False | Filter results to items with ID greater than or equal to specified value |
| `id__lt` | integer | False | Filter results to items with ID less than specified value |
| `id__lte` | integer | False | Filter results to items with ID less than or equal to specified value |
| `update_ts__lt` | timestamp | False | Filter for net_device_metrics records with any fields updated before this filter's value |
| `update_ts__gt` | timestamp | False | Filter for net_device_metrics records with any fields updated after this filter's value |
| `bmask_applied` | boolean | False | Indicates whether band masking is applied |
| `limit` | int | False | Restricts the number of records returned in a recordset to this value. Max value is 500. |
| `offset` | int | False | Specifies where (an index) in a recordset to begin returning records. |

### Response Fields

| Field | Type | Sample Value |
|-------|------|--------------|
| `bmask_applied` | null | null |
| `bytes_in` | int | 79220 |
| `bytes_out` | int | 66603 |
| `cell_id` | null | null |
| `cinr` | null | null |
| `dbm` | null | null |
| `ecio` | null | null |
| `id` | str | 1962784 |
| `lac` | null | null |
| `mcc` | null | null |
| `mnc` | null | null |
| `net_device` | str | https://www.us0.cradlepointecm.com/api/v2/net_devices/196278... |
| `resource_url` | str | https://www.us0.cradlepointecm.com/api/v2/net_device_metrics... |
| `rsrp` | null | null |
| `rsrq` | null | null |
| `rssi` | null | null |
| `rssnr` | null | null |
| `service_type` | str | Not Available |
| `signal_strength` | null | null |
| `sinr` | null | null |
| `tac` | null | null |
| `update_ts` | null | null |

---

## net_device_signal_samples

```
GET /api/v2/net_device_signal_samples/
```

### Query Parameters

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `net_device` | in: int<br />out: url | False | ID of a net device |
| `net_device__in` | in: int<br />out: url | False | Filter for net_device contains - a comma-separated list of net_device IDs |
| `created_at` | timestamp | False | Timestamp for when the net_device_signal_samples record was created |
| `created_at__lt` | timestamp | False | Filter for created_at is less than |
| `created_at__gt` | timestamp | False | Filter for created_at is greater than |
| `created_at_timeuuid` | timeuuid | False | A unique ID (timeuuid) associated with the created_at timestamp |
| `created_at_timeuuid__in` | timeuuid | False | Filter for created_at_timeuuid in - a comma-separated list of timeuuids for net_device_signal_samples records |
| `created_at_timeuuid__gt` | timeuuid | False | Filter for created_at_timeuuid is greater than |
| `created_at_timeuuid__gte` | timeuuid | False | Filter for created_at_timeuuid is greater than or equal to |
| `created_at_timeuuid__lt` | timeuuid | False | Filter for created_at_timeuuid is less than |
| `created_at_timeuuid__lte` | timeuuid | False | Filter for created_at_timeuuid is less than or equal |
| `order_by` | string | False | Specifies the sort order of response data |
| `limit` | int | False | Restricts the number of records returned in a recordset to this value. Max value is 500. |

---

## net_device_usage_samples

```
GET /api/v2/net_device_usage_samples/
```

### Query Parameters

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `net_device` | in: int<br />out: url | False | ID of a net device |
| `net_device__in` | in: int<br />out: url | False | Filter for net_device contains - a comma-separated list of net_device IDs |
| `created_at` | timestamp | False | Timestamp for when the net_device_usage_samples record was created |
| `created_at__lt` | timestamp | False | Filter for created_at is less than |
| `created_at__gt` | timestamp | False | Filter for created_at is greater than |
| `created_at_timeuuid` | timeuuid | False | A unique ID (timeuuid) associated with the created_at timestamp |
| `created_at_timeuuid__in` | timeuuid | False | Filter for created_at_timeuuid in - a comma-separated list of timeuuids for net_device_usage_samples records |
| `created_at_timeuuid__gt` | timeuuid | False | Filter for created_at_timeuuid is greater than |
| `created_at_timeuuid__gte` | timeuuid | False | Filter for created_at_timeuuid is greater than or equal to |
| `created_at_timeuuid__lt` | timeuuid | False | Filter for created_at_timeuuid is less than |
| `created_at_timeuuid__lte` | timeuuid | False | Filter for created_at_timeuuid is less than or equal |
| `order_by` | string | False | Specifies the sort order for response data |
| `limit` | int | False | Restricts the number of records returned in a recordset to this value. Max value is 500. |
| `offset` | int | False | Specifies where (an index) in a recordset to begin returning records. |

---

## products

```
GET /api/v2/products/
```

### Query Parameters

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `id` | int | False | ID of a products record |
| `id__in` | int | False | Filter for ID contains - a comma-separated list of IDs |
| `limit` | int | False | Restricts the number of records returned in a recordset to this value. Max value is 500. |
| `offset` | int | False | Specifies where (an index) in a recordset to begin returning records. |

### Response Fields

| Field | Type | Sample Value |
|-------|------|--------------|
| `device_type` | str | router |
| `id` | str | 1 |
| `name` | str | MBR1400 |
| `resource_url` | str | https://www.us0.cradlepointecm.com/api/v2/products/1/ |
| `series` | int | 3 |

---

## reboot_activity

```
GET /api/v2/reboot_activity/
```

---

## router_alerts

```
GET /api/v2/router_alerts/
```

### Query Parameters

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `router` | in: int<br />out: url | False | Router ID |
| `router__in` | in: int<br />out: url | False | Filter for router ID contains - a comma-separated list of router-record IDs |
| `created_at` | timestamp | False | Timestamp for when the router_alerts record was created |
| `created_at__lt` | timestamp | False | Less than filtering operator for created_at |
| `created_at__gt` | timestamp | False | Filter for created_at is greater than |
| `created_at_timeuuid` | timeuuid | False | A unique ID (timeuuid) associated with the created_at timestamp |
| `created_at_timeuuid__in` | timeuuid | False | Filter for created_at_timeuuid in - a comma-separated list of timeuuids for router_alerts records |
| `created_at_timeuuid__gt` | timeuuid | False | Filter for created_at_timeuuid is greater than |
| `created_at_timeuuid__gte` | timeuuid | False | Filter for created_at_timeuuid is greater than or equal to |
| `created_at_timeuuid__lt` | timeuuid | False | Filter for created_at_timeuuid is less than |
| `created_at_timeuuid__lte` | timeuuid | False | Filter for created_at_timeuuid is less than or equal |
| `order_by` | string | False | Specifies the sort order for response data |
| `limit` | int | False | Restricts the number of records returned in a recordset to this value. Max value is 500. |
| `offset` | int | False | Specifies where (an index) in a recordset to begin returning records. |

### Response Fields

| Field | Type | Sample Value |
|-------|------|--------------|
| `created_at` | str | 2026-06-06T12:59:12.462000+00:00 |
| `created_at_timeuuid` | str | 83d52c38-61a7-11f1-a2f3-922705407062 |
| `detected_at` | str | 2026-06-06T12:59:11.778021+00:00 |
| `friendly_info` | str | IPsec Tunnel "vti" has gone down. |
| `info` | dict | {'time': ['2026-06-06 12:59:11', 'UTC'], 'tunname': 'vti', '... |
| `router` | str | https://www.us0.cradlepointecm.com/api/v2/routers/4618577/ |
| `type` | str | ipsec_tunnel_down |

---

## router_logs

```
GET /api/v2/router_logs/
```

### Query Parameters

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `router` | in: int<br />out: url | True | ID of the Router to retrieve logs from |
| `created_at` | timestamp | False | Timestamp for when the router_logs record was created |
| `created_at__lt` | timestamp | False | Filter for created_at is less than |
| `created_at__gt` | timestamp | False | Filter for created_at is greater than |
| `created_at_timeuuid` | timeuuid | False | A unique ID (timeuuid) associated with the created_at timestamp |
| `created_at_timeuuid__in` | timeuuid | False | Filter for created_at_timeuuid in - a comma-separated list of timeuuids for router_logs records |
| `created_at_timeuuid__gt` | timeuuid | False | Filter for created_at_timeuuid is greater than |
| `created_at_timeuuid__gte` | timeuuid | False | Filter for created_at_timeuuid is greater than or equal to |
| `created_at_timeuuid__lt` | timeuuid | False | Filter for created_at_timeuuid is less than |
| `created_at_timeuuid__lte` | timeuuid | False | Filter for created_at_timeuuid is less than or equal |
| `order_by` | string | False | Specifies the sort order for response data |
| `limit` | int | False | Restricts the number of records returned in a recordset to this value. Max value is 500. |
| `offset` | int | False | Specifies where (an index) in a recordset to begin returning records. |

---

## router_state_samples

```
GET /api/v2/router_state_samples/
```

### Query Parameters

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `router` | in: int<br />out: url | False | Router ID |
| `router__in` | in: int<br />out: url | False | Filter for router ID contains - a comma-separated list of router-record IDs |
| `created_at` | timestamp | False | Timestamp for when the router_state_samples record was created |
| `created_at__lt` | timestamp | False | Less than filtering operator for created_at |
| `created_at__gt` | timestamp | False | Filter for created_at is greater than |
| `created_at_timeuuid` | timeuuid | False | A unique ID (timeuuid) associated with the created_at timestamp |
| `created_at_timeuuid__in` | timeuuid | False | Filter for created_at_timeuuid in - a comma-separated list of timeuuids for router_state_samples records |
| `created_at_timeuuid__gt` | timeuuid | False | Filter for created_at_timeuuid is greater than |
| `created_at_timeuuid__gte` | timeuuid | False | Filter for created_at_timeuuid is greater than or equal to |
| `created_at_timeuuid__lt` | timeuuid | False | Filter for created_at_timeuuid is less than |
| `created_at_timeuuid__lte` | timeuuid | False | Filter for created_at_timeuuid is less than or equal |
| `order_by` | string | False | Specifies the sort order for response data |
| `limit` | int | False | Restricts the number of records returned in a recordset to this value. Max value is 500. |
| `offset` | int | False | Specifies where (an index) in a recordset to begin returning records. |

---

## router_stream_usage_samples

```
GET /api/v2/router_stream_usage_samples/
```

### Query Parameters

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `router` | in: int<br />out: url | False | Router ID |
| `router__in` | in: int<br />out: url | False | Filter for router ID contains - a comma-separated list of router-record IDs |
| `created_at` | timestamp | False | Timestamp for when the router_stream_usage_samples record was created |
| `created_at__lt` | timestamp | False | Less than filtering operator for created_at |
| `created_at__gt` | timestamp | False | Filter for created_at is greater than |
| `created_at_timeuuid` | timeuuid | False | A unique ID (timeuuid) associated with the created_at timestamp |
| `created_at_timeuuid__in` | timeuuid | False | Filter for created_at_timeuuid in - a comma-separated list of timeuuids for router_stream_usage_samples records |
| `created_at_timeuuid__gt` | timeuuid | False | Filter for created_at_timeuuid is greater than |
| `created_at_timeuuid__gte` | timeuuid | False | Filter for created_at_timeuuid is greater than or equal to |
| `created_at_timeuuid__lt` | timeuuid | False | Filter for created_at_timeuuid is less than |
| `created_at_timeuuid__lte` | timeuuid | False | Filter for created_at_timeuuid is less than or equal |
| `order_by` | string | False | Specifies the sort order for response data |
| `limit` | int | False | Restricts the number of records returned in a recordset to this value. Max value is 500. |
| `offset` | int | False | Specifies where (an index) in a recordset to begin returning records. |

---

## routers

```
GET /api/v2/routers/
```

### Query Parameters

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `account` | in: int<br />out: url | False | Account that owns the routers record object |
| `account__in` | in: int<br />out: url | False | Filter for account contains - a comma-separated list of account IDs |
| `group` | in: int<br />out: url | False | Optional group this device belongs to |
| `group__in` | in: int<br />out: url | False | Filter for group contains - a comma-separated list of group IDs |
| `id` | int | False | Routers record object ID |
| `id__in` | int | False | Filter for ID contains - a comma-separated list of IDs |
| `id__gt` | integer | False | Filter results to items with ID greater than specified value (cursor pagination) |
| `id__gte` | integer | False | Filter results to items with ID greater than or equal to specified value |
| `id__lt` | integer | False | Filter results to items with ID less than specified value |
| `id__lte` | integer | False | Filter results to items with ID less than or equal to specified value |
| `ipv4_address` | string | False | Device's IPv4 address |
| `ipv4_address__in` | string | False | Filter for IPV4 address contains - a comma-separated list of IP addresses |
| `mac` | string | False | Device's MAC address |
| `mac__in` | string | False | Filter for MAC address contains - a comma-separated list of MAC addresses |
| `name` | string | False | Device's name (synched with device) |
| `name__in` | string | False | Filter for device name contains - a comma-separated list of device names |
| `state` | string | False | Device's state: initialized, online or offline |
| `state__in` | string | False | Filter for state contains - a comma-separated list of states |
| `state_updated_at__lt` | timestamp | False | Filter for state_updated_at is less than |
| `state_updated_at__gt` | timestamp | False | Filter for state_updated_at is greater than |
| `updated_at__lt` | timestamp | False | Filter for updated_at is less than |
| `updated_at__gt` | timestamp | False | Filter for updated_at is greater than |
| `expand` | string | False | Specifies that the returned value for the passed in attribute be expanded in the response body. |
| `limit` | int | False | Restricts the number of records returned in a recordset to this value. Max value is 500. |
| `offset` | int | False | Specifies where (an index) in a recordset to begin returning records. |

### Response Fields

| Field | Type | Sample Value |
|-------|------|--------------|
| `account` | str | https://www.us0.cradlepointecm.com/api/v2/accounts/307/ |
| `actual_firmware` | str | https://www.us0.cradlepointecm.com/api/v2/firmwares/535/ |
| `asset_id` | null | null |
| `config_status` | str | pending |
| `configuration_manager` | str | https://www.us0.cradlepointecm.com/api/v2/routers/371193/con... |
| `created_at` | str | 2016-04-13T21:29:11.490817+00:00 |
| `custom1` | null | null |
| `custom2` | null | null |
| `description` | null | null |
| `device_type` | str | router |
| `full_product_name` | str | CBA850 |
| `group` | str | https://www.us0.cradlepointecm.com/api/v2/groups/17045/ |
| `id` | str | 371193 |
| `ipv4_address` | str | 166.241.162.156 |
| `lans` | str | https://www.us0.cradlepointecm.com/api/v2/routers/371193/lan... |
| `last_known_location` | str | https://www.us0.cradlepointecm.com/api/v2/locations/456543/ |
| `locality` | str | US/Mountain |
| `mac` | str | 00:30:44:1C:38:D0 |
| `name` | str | Desk850 |
| `overlay_network_binding` | str | https://www.us0.cradlepointecm.com/api/v2/routers/371193/ove... |
| `product` | str | https://www.us0.cradlepointecm.com/api/v2/products/27/ |
| `reboot_required` | bool | False |
| `resource_url` | str | https://www.us0.cradlepointecm.com/api/v2/routers/371193/ |
| `serial_number` | str | MM150030500235 |
| `state` | str | offline |
| `state_updated_at` | str | 2018-05-07T18:41:51.237597+00:00 |
| `target_firmware` | str | https://www.us0.cradlepointecm.com/api/v2/firmwares/535/ |
| `updated_at` | str | 2020-11-11T23:08:00.746990+00:00 |
| `upgrade_pending` | bool | False |

---

## speed_test

```
GET /api/v2/speed_test/
```

---

## users

```
GET /api/v2/users/
```

### Query Parameters

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `id` | int | False | User ID |
| `username` | string | False | Username of a user |
| `email` | string | False | A user's email address |
| `limit` | int | False | Restricts the number of records returned in a recordset to this value. Max value is 500. |
| `offset` | int | False | Specifies where (an index) in a recordset to begin returning records. |

### Response Fields

| Field | Type | Sample Value |
|-------|------|--------------|
| `account` | str | https://www.us0.cradlepointecm.com/api/v2/accounts/3644/ |
| `email` | str | mitchell.meade@ericsson.com |
| `first_name` | str | Mitchell |
| `id` | str | 167 |
| `last_name` | str | Meade |
| `resource_url` | str | https://www.us0.cradlepointecm.com/api/v2/users/167/ |
| `username` | str | 54qGBJ7ZqGMjbIFK |

---

