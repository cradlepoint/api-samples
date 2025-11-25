#!/usr/bin/env php
<?php
/**
 * Script to generate a CSV report of licensed routers from subscriptions
 * and identify unlicensed routers.
 *
 * This script:
 * 1. Gets all subscriptions with end_time later than yesterday
 * 2. Gets all asset_endpoints from the system
 * 3. Correlates asset_endpoints with subscriptions by matching subscription IDs
 * 4. Creates a CSV report with router MAC, serial, subscription details
 * 5. Identifies unlicensed routers (not in any subscription)
 */

// Optional: Set your NCM API v3 token here, or use NCM_API_TOKEN/TOKEN environment variable
$NCM_API_TOKEN = ''; // Set to your token string if you want to hardcode it

// Base URL for Cradlepoint NCM API v3
define('API_BASE_URL', 'https://api.cradlepointecm.com/api/v3');

function get_yesterday_iso() {
    /** Get yesterday's date in ISO format (YYYY-MM-DDTHH:MM:SSZ) */
    $yesterday = new DateTime('yesterday', new DateTimeZone('UTC'));
    return $yesterday->format('Y-m-d\T00:00:00\Z');
}

function make_api_request($endpoint, $token, $params = []) {
    /**
     * Make an API request with pagination support.
     * Returns all paginated results.
     */
    $url = API_BASE_URL . $endpoint;
    
    // Add query parameters
    if (!empty($params)) {
        $queryString = http_build_query($params);
        $url .= '?' . $queryString;
    }
    
    $all_results = [];
    $current_url = $url;
    $page_num = 1;
    
    while ($current_url) {
        $ch = curl_init();
        curl_setopt_array($ch, [
            CURLOPT_URL => $current_url,
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_HTTPHEADER => [
                'Authorization: Bearer ' . $token,
                'Content-Type: application/vnd.api+json',
                'Accept: application/vnd.api+json'
            ],
            CURLOPT_TIMEOUT => 30
        ]);
        
        $response = curl_exec($ch);
        $http_code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        curl_close($ch);
        
        if ($http_code < 200 || $http_code >= 300) {
            echo "    Error fetching page $page_num: HTTP $http_code\n";
            break;
        }
        
        $json_data = json_decode($response, true);
        
        if (isset($json_data['data'])) {
            if (is_array($json_data['data'])) {
                $all_results = array_merge($all_results, $json_data['data']);
                if ($page_num % 10 == 0) {
                    echo "    Fetched " . count($all_results) . " items so far (page $page_num)...\n";
                }
            } else {
                $all_results[] = $json_data['data'];
            }
        }
        
        // Check for next page
        if (isset($json_data['links']['next'])) {
            $next_url = $json_data['links']['next'];
            if ($next_url === $current_url) {
                echo "    Warning: Next page URL is same as current, stopping pagination\n";
                break;
            }
            $current_url = $next_url;
            $page_num++;
        } else {
            $current_url = null;
        }
    }
    
    return $all_results;
}

function get_subscriptions_with_asset_endpoints($end_time_gt, $token) {
    /**
     * Get all subscriptions with end_time greater than the specified date.
     * Returns subscriptions with their asset_endpoints relationship links.
     */
    $start_time = microtime(true);
    echo "Fetching subscriptions with end_time > $end_time_gt...\n";
    
    $subscriptions = make_api_request('/subscriptions', $token, [
        'filter[end_time][gt]' => $end_time_gt,
        'page[size]' => 50
    ]);
    
    $elapsed = microtime(true) - $start_time;
    
    if (empty($subscriptions)) {
        echo "No subscriptions found.\n";
        return [];
    }
    
    echo "Found " . count($subscriptions) . " subscriptions in " . number_format($elapsed, 2) . " seconds.\n";
    return $subscriptions;
}

function get_all_asset_endpoints($token) {
    /**
     * Get all asset_endpoints from the system.
     */
    $start_time = microtime(true);
    echo "Fetching all asset_endpoints...\n";
    
    $asset_endpoints = make_api_request('/asset_endpoints', $token, [
        'page[size]' => 50
    ]);
    
    $elapsed = microtime(true) - $start_time;
    echo "Found " . count($asset_endpoints) . " total asset_endpoints in " . number_format($elapsed, 2) . " seconds.\n";
    return $asset_endpoints;
}

function correlate_subscriptions_and_asset_endpoints($subscriptions, $asset_endpoints) {
    /**
     * Correlate asset_endpoints with subscriptions by matching subscription IDs.
     * Returns:
     *   - Array of CSV rows with subscription data
     *   - Array of (mac_address, serial_number) tuples for licensed routers (as keys for fast lookup)
     */
    $start_time = microtime(true);
    
    // Build a map of subscription_id -> subscription details
    $subscription_map = [];
    foreach ($subscriptions as $subscription) {
        $sub_id = $subscription['id'] ?? '';
        $attributes = $subscription['attributes'] ?? [];
        $subscription_map[$sub_id] = [
            'name' => $attributes['name'] ?? '',
            'start_time' => $attributes['start_time'] ?? '',
            'end_time' => $attributes['end_time'] ?? '',
            'id' => $sub_id
        ];
    }
    
    echo "Built subscription map with " . count($subscription_map) . " subscriptions\n";
    
    // Process asset_endpoints and match them to subscriptions
    $csv_rows = [];
    $licensed_combos = []; // Using array keys for fast lookup
    
    foreach ($asset_endpoints as $asset_endpoint) {
        $asset_attrs = $asset_endpoint['attributes'] ?? [];
        $relationships = $asset_endpoint['relationships'] ?? [];
        
        $mac_address = $asset_attrs['mac_address'] ?? '';
        $serial_number = $asset_attrs['serial_number'] ?? '';
        
        if (empty($mac_address) || empty($serial_number)) {
            continue;
        }
        
        // Check if this asset_endpoint has subscriptions in relationships
        $subscription_ids = [];
        if (isset($relationships['subscriptions']['data'])) {
            $subscriptions_data = $relationships['subscriptions']['data'];
            if (is_array($subscriptions_data)) {
                foreach ($subscriptions_data as $sub) {
                    if (isset($sub['id'])) {
                        $subscription_ids[] = $sub['id'];
                    }
                }
            } elseif (isset($subscriptions_data['id'])) {
                $subscription_ids[] = $subscriptions_data['id'];
            }
        }
        
        // Match to subscriptions that have end_time > yesterday
        foreach ($subscription_ids as $sub_id) {
            if (isset($subscription_map[$sub_id])) {
                $sub_info = $subscription_map[$sub_id];
                $csv_rows[] = [
                    'mac_address' => $mac_address,
                    'serial_number' => $serial_number,
                    'subscription_start_time' => $sub_info['start_time'],
                    'subscription_end_time' => $sub_info['end_time'],
                    'subscription_name' => $sub_info['name'],
                    'id' => $sub_id
                ];
                // Use combo as key for fast lookup
                $combo = strtolower($mac_address) . '|' . $serial_number;
                $licensed_combos[$combo] = true;
            }
        }
    }
    
    $elapsed = microtime(true) - $start_time;
    echo "Correlated " . count($asset_endpoints) . " asset_endpoints with subscriptions in " . number_format($elapsed, 2) . " seconds.\n";
    echo "Found " . count($csv_rows) . " licensed router entries.\n";
    return [$csv_rows, $licensed_combos];
}

function identify_unlicensed_routers($asset_endpoints, $licensed_combos) {
    /**
     * Identify routers that are not in any subscription (unlicensed).
     */
    $start_time = microtime(true);
    $unlicensed_rows = [];
    
    foreach ($asset_endpoints as $asset_endpoint) {
        $asset_attrs = $asset_endpoint['attributes'] ?? [];
        $mac_address = $asset_attrs['mac_address'] ?? '';
        $serial_number = $asset_attrs['serial_number'] ?? '';
        
        if (!empty($mac_address) && !empty($serial_number)) {
            $combo = strtolower($mac_address) . '|' . $serial_number;
            if (!isset($licensed_combos[$combo])) {
                $unlicensed_rows[] = [
                    'mac_address' => $mac_address,
                    'serial_number' => $serial_number,
                    'subscription_start_time' => 'UNLICENSED',
                    'subscription_end_time' => 'UNLICENSED',
                    'subscription_name' => 'UNLICENSED',
                    'id' => 'UNLICENSED'
                ];
            }
        }
    }
    
    $elapsed = microtime(true) - $start_time;
    echo "Identified unlicensed routers in " . number_format($elapsed, 2) . " seconds.\n";
    return $unlicensed_rows;
}

function write_csv_report($csv_rows, $output_file = 'subscription_report.csv') {
    /**
     * Write the CSV report to a file.
     */
    if (empty($csv_rows)) {
        echo "No data to write to CSV.\n";
        return;
    }
    
    $start_time = microtime(true);
    $fieldnames = ['mac_address', 'serial_number', 'subscription_start_time', 
                  'subscription_end_time', 'subscription_name', 'id'];
    
    echo "Writing " . count($csv_rows) . " rows to $output_file...\n";
    
    $fp = fopen($output_file, 'w');
    if ($fp === false) {
        echo "Error: Could not open file $output_file for writing.\n";
        return;
    }
    
    // Write BOM for Excel compatibility
    fwrite($fp, "\xEF\xBB\xBF");
    
    // Write header
    fputcsv($fp, $fieldnames);
    
    // Write rows
    foreach ($csv_rows as $row) {
        fputcsv($fp, [
            $row['mac_address'],
            $row['serial_number'],
            $row['subscription_start_time'],
            $row['subscription_end_time'],
            $row['subscription_name'],
            $row['id']
        ]);
    }
    
    fclose($fp);
    
    $elapsed = microtime(true) - $start_time;
    echo "CSV report written to $output_file in " . number_format($elapsed, 2) . " seconds.\n";
}

function main() {
    /** Main function to run the script. */
    $script_start_time = microtime(true);
    
    global $NCM_API_TOKEN;
    
    // Get token from script variable or environment variable
    $token = $NCM_API_TOKEN ?: (getenv('NCM_API_TOKEN') ?: getenv('TOKEN'));
    
    if (empty($token)) {
        echo "Error: NCM API token not found. Please set NCM_API_TOKEN in the script or as an environment variable.\n";
        exit(1);
    }
    
    // Get yesterday's date in ISO format
    $yesterday_iso = get_yesterday_iso();
    echo "Filtering subscriptions with end_time > $yesterday_iso\n\n";
    
    // Step 1: Get all subscriptions with end_time > yesterday
    $subscriptions = get_subscriptions_with_asset_endpoints($yesterday_iso, $token);
    
    if (empty($subscriptions)) {
        echo "No subscriptions found. Exiting.\n";
        return;
    }
    
    // Step 2: Get all asset_endpoints
    $all_asset_endpoints = get_all_asset_endpoints($token);
    
    // Step 3: Correlate asset_endpoints with subscriptions
    list($csv_rows, $licensed_combos) = correlate_subscriptions_and_asset_endpoints($subscriptions, $all_asset_endpoints);
    
    echo "\nTotal licensed routers found: " . count($csv_rows) . "\n";
    echo "Unique licensed MAC/serial combos: " . count($licensed_combos) . "\n";
    
    // Step 4: Identify unlicensed routers
    $unlicensed_rows = identify_unlicensed_routers($all_asset_endpoints, $licensed_combos);
    
    echo "Unlicensed routers found: " . count($unlicensed_rows) . "\n";
    
    // Step 5: Combine licensed and unlicensed rows
    $all_csv_rows = array_merge($csv_rows, $unlicensed_rows);
    
    // Step 6: Write CSV report
    write_csv_report($all_csv_rows);
    
    $total_elapsed = microtime(true) - $script_start_time;
    echo "\n" . str_repeat('=', 60) . "\n";
    echo "Script completed successfully!\n";
    echo "Total execution time: " . number_format($total_elapsed, 2) . " seconds (" . number_format($total_elapsed / 60, 2) . " minutes)\n";
    echo str_repeat('=', 60) . "\n";
}

// Run the script
main();

