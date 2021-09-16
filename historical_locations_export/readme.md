# historical_locations_export.py
This is a Python script to export data from the Cradlepoint NCM API historical_locations/
endpoint and write it to .csv file.  The .csv file can be dropped into http://kepler.gl/demo
to create maps based on data such as signal strength

1. Enter Cradlepoint NCM API Keys at top of script
    ```
	api_keys = {'X-ECM-API-ID': 'YOUR',
	           'X-ECM-API-KEY': 'KEYS',
               'X-CP-API-ID': 'GO',
               'X-CP-API-KEY': 'HERE',
        	   'Content-Type': 'application/json'}
    ```

2. Set start_date and end_date for data you want to capture
    ```
    start_date = '2021-09-01'
	end_date = '2021-09-04'
    ```
3. Set output filename (optional)
	```
	output_file = 'historical_locations.csv'
	```

4. Run script - this can take a long time if there is a lot of data to export!
5. 
Fields Exported:
"router", "name", "accuracy", "carrier_id", "cinr", "created_at", "created_at_timeuuid", "dbm", "ecio", "latitude", "longitude", "mph", "net_device_name", "rfband", "rfband_5g", "rsrp", "rsrp_5g", "rsrq", "rsrq_5g", "rssi", "signal_percent", "sinr", "sinr_5g", "summary"
	    
5. Drag and drop output .csv file to http://kepler.gl/demo to create maps based on data
such as signal strength.
