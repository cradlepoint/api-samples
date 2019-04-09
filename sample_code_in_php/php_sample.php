<?php
$url = 'https://www.cradlepointecm.com/api/v2/routers/';
$headers = array(
    'X-CP-API-ID: ...',
    'X-CP-API-KEY: ...',
    'X-ECM-API-ID: ...',
    'X-ECM-API-KEY: ...',
    'Content-Type: application/json'
);

$req = curl_init();
curl_setopt_array($req, array(
    CURLOPT_URL => $url,
 CURLOPT_HTTPHEADER => $headers,
));

$result = curl_exec($req);
$res_info = curl_getinfo($req);
echo $res_info['http_code'];
curl_close($req);
?>
