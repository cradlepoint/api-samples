# NCX_resources
### Create an NCX IP Subnet resource on site for all LANs on all routers in specified NCM group. 

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
     pip install ncm
     ```

3. **Configure the Application:**
   - Open `NCX_resources.py` in a text editor.
   - Modify the following variables at the top of the file with your specific details:
     - **NCM Source Group ID**
     - **NCX Network ID**
     - **NCM API Keys**


5. **Run the Application:**
   - Execute the application by running:
     ```sh
     python NCX_resources.py
     ```

### The application will:
- Create NCX IP Subnet resources on site for all LANs on each router.
- Output status and results.