### Step 0: Install Python

Before installing the necessary packages and running the scripts, make sure you have Python installed on your system.

1. **Check if Python is installed:**

    Open a terminal or command prompt and run the following command:

    ```bash
    python3 --version
    ```

    If Python is installed, this command will return the version number. If not, proceed to the next step.

2. **Install Python:**

    If Python is not installed, download and install it from the official [Python website](https://www.python.org/downloads/). Make sure to download Python 3.x.

    During installation, ensure that you check the option to "Add Python to PATH."


### Before Running the Scripts

Before running the scripts, make sure to install the following packages using `pip`:

```bash
pip install pygame
pip install threading
pip install json
pip install adafruit-circuitpython-busdevice
pip install RPi.GPIO
pip install adafruit-circuitpython-scd30
pip install nfcpy
pip install sktwriter
pip install paho-mqtt
pip install influxdb-client
```
### Steps to Run the Scripts

1. **Step 1**: Run the CO2 sensor script
    ```bash
    python3 co2.py
    ```

2. **Step 2**: Run the main script
    ```bash
    python3 main.py
    ```
