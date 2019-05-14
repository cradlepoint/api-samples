disable_wifi.py is a very basic script that disables the wifi on a given list of routers.  It uses an HTTP PATCH so that
only WiFi is disabled and your entire configuration doesn't get overwritten.

This script could easily be modified to patch or put other configurations. Simply replace the payload with a different
json payload that you want to send to your routers.

Made by Harvey Breaux for use with the Cradlepoint NCM APIv2