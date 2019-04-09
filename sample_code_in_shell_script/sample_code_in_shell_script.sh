ECM_API_ID="<ECM-API-ID HERE>"
ECM_API_KEY="<ECM-API-KEY HERE>"
CP_API_ID="<CP-API-ID HERE>"
CP_API_KEY="<CP-API-KEY HERE>"
URL="https://cradlepointecm.com/api/v2/accounts/"
curl -H "X-ECM-API-ID: $ECM_API_ID" -H "X-ECM-API-KEY: $ECM_API_KEY"
     -H "X-CP-API-ID: $CP_API_ID" -H "X-CP-API-KEY: $CP_API_KEY"
     -H "Content-Type: application/json" $URL
