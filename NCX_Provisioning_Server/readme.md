# NCX Provisioning Server
**Version:** v0.1.0

![image](https://github.com/user-attachments/assets/b001c679-2be5-4310-a638-f49e21cfd0cf)

## Setup

### Requirements:
- A computer with Python 3.8 or newer
- PIP (Python package manager)

### Steps:
1. **Download and Unzip the Application:**
   - Obtain the app and extract the files to your preferred directory.

2. **Install Dependencies:**
   - Open a command prompt in the app’s directory.
   - Run the following command to install the required Python packages:
     ```sh
     pip install -r requirements.txt
     ```

3. **Create the `routers.csv` File:**
   - This file should include columns for `serial_number`, `mac`, and `lan_subnet`.
   - An example file is provided in the app package for reference.

4. **Configure the Application:**
   - Open `NCX_Provisioning_Server.py` in a text editor.
   - Modify the following variables at the top of the file with your specific details:
     - **NCM API Keys**
     - **Subscriptions to be added**
     - **Production Group ID**
     - **NCX Network ID**
     - **CSV Filename** (e.g., `routers.csv`)
     - **LAN UIDs** (PrimaryLAN is provided by default)

   - If needed, update the column header names in `routers.csv` to match your data.

5. **Run the Application:**
   - Execute the application by running:
     ```sh
     python NCX_Provisioning_Server.py
     ```

## Usage

1. The application runs a web server on port **8888**.
2. To access the interface, open a web browser and go to: [http://localhost:8888](http://localhost:8888).
3. **Adding Routers:**
   - Click the **Add** button.
   - Enter the router's MAC address or Serial Number along with its Name.
4. **Provisioning Routers:**
   - When you are ready, click **Submit** to start provisioning.

### The application will:
- Apply the specified licenses.
- Move the router to the specified group.
- Configure the router’s name and LAN subnet.
- Create an NCX Site for the router.
- Create an NCX Resource for the LAN subnet.
