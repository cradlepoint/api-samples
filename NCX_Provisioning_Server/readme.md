
NCX_Provisioning_Server
================
v0.1.0

![image](https://github.com/user-attachments/assets/b001c679-2be5-4310-a638-f49e21cfd0cf)

Setup
=====================
Computer with Python 3.8 or newer and PIP  
Download and unzip the app.  
From a command prompt in the app folder, type:  
**pip install -r requirements.txt**  

Create routers.csv with columns for serial_number, mac, and lan_subnet.  
An example has been provided.  

Edit NCX_Provisioning_Server.py and enter your info at the top:
> NCM API Keys  
> Subscriptions to be added  
> Production Group ID  
> NCX Network ID  
> CSV Filename (routers.csv)  
> LAN UIDs (PrimaryLAN is provided)  

Edit the column header names if necessary.

Then run the application:  
**python NCX_Provisioning_Server.py**

Usage
===================
This app runs a webserver on port 8000.  
Browse to http://localhost:8000  
Click Add, then enter router MAC or Serial Number and Name.  
When ready to provision routers, click submit.    

The app will apply the specified licenses,   
move the router to the specified group,  
configure the router name and LAN subnet,  
create an NCX Site for the router,  
and create an NCX Resource for the LAN subnet.  

