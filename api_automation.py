import json
import csv
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# AchtBytes API URL (telemetry data)
API_URL = "https://iot.achtbytes.com/copc/api/devices/95ddf841-f45b-44fb-94ac-d41ca67a091d/assets/f61f0a65-6157-4999-82c4-8fd3941d6b8a/telemetry?telemetryIds=PI_SSP_PDI32_MSDC32_Ampere_1&telemetryIds=PI_SSP_PDI32_MSDC32_Ampere_2&telemetryIds=PI_SSP_PDI32_MSDC32_Ampere_3&fromDate=2025-03-08T23%3A47%3A38.780Z&toDate=2025-03-09T23%3A47%3A38.780Z"

# AchtBytes Login Credentials (REPLACE THESE)
EMAIL = "vtn96492@uga.edu"
PASSWORD = "Capstone25!"

# Chrome WebDriver setup with CDP enabled
chrome_options = Options()
# chrome_options.add_argument("--headless")  # Run in headless mode
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--remote-debugging-port=9222")

# Path to your ChromeDriver (modify if needed)
service = Service("/usr/local/bin/chromedriver")  # Change this path if necessary
driver = webdriver.Chrome(service=service, options=chrome_options)

# Enable Chrome DevTools Protocol (CDP)
devtools = driver.execute_cdp_cmd

# Open AchtBytes login page
driver.get("https://iot.achtbytes.com/login")

# wait for everything to load

time.sleep(15)

# Find username and password fields (modify if necessary)
driver.find_element(By.ID, "signInName").send_keys(EMAIL)
driver.find_element(By.ID, "password").send_keys(PASSWORD + Keys.RETURN)

# Wait for login to complete
time.sleep(15)

# finding the assets button and clicking it
driver.find_element(By.ID, "nav-item-assets-overview").click()

time.sleep(5)

# getting all the online assets that we can get data from
online_cards = driver.find_elements(By.XPATH, "//a[contains(@class, 'overview-link') and .//span[text()='Online']]")

time.sleep(2) 

bearer_tokens = []
telemetry_requests = {}

driver.execute_cdp_cmd("Network.enable", {})

# Intercept network requests and capture the Bearer token & telemetry URLs
def intercept_request(params):
    global bearer_tokens, telemetry_requests
    request = params.get("request", {})
    headers = request.get("headers", {})
    url = request.get("url", "")

    # Capture Bearer token
    if "Authorization" in headers and "Bearer" in headers["Authorization"]:
        token = headers["Authorization"].split("Bearer ")[1]
        bearer_tokens.append(token)
        print(f"🔑 Bearer Token Captured: {token}")

    # Capture telemetry request URLs with their respective token
    if "telemetry" in url:
        telemetry_requests[url] = token
        print(f"📡 Telemetry Request Captured: {url} → Token: {token}")

# Attach request listener (use WebDriver's built-in logging)
driver.execute_cdp_cmd("Network.setRequestInterception", {"patterns": [{"urlPattern": "*"}]})
driver.execute_cdp_cmd("Network.onRequestWillBeSent", intercept_request)

for card in online_cards:
    time.sleep(10)
    card.click()

    try:
        WebDriverWait(driver, 10).until(lambda driver: len(telemetry_requests) > 0)
        print(f"✅ Captured {len(telemetry_requests)} Telemetry Requests.")
    except:
        print("❌ No telemetry requests captured within the timeout.")

    # ✅ STEP 6: Ensure Tokens Are Captured
    if bearer_tokens:
        print(f"✅ Captured {len(bearer_tokens)} Bearer Tokens.")
    else:
        print("❌ Failed to retrieve Bearer tokens.")

time.sleep(15)

driver.quit()

# Make the API request with the retrieved token
# import requests

# headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
# response = requests.get(API_URL, headers=headers)

# if response.status_code == 200:
#     data = response.json()

#     # Save JSON data
#     with open("telemetry_data.json", "w") as json_file:
#         json.dump(data, json_file, indent=4)
#     print("✅ Data saved to telemetry_data.json")

#     # Convert JSON to CSV
#     with open("telemetry_data.csv", "w", newline="") as csv_file:
#         csv_writer = csv.writer(csv_file)
#         csv_writer.writerow(["telemetry_id", "timestamp", "value"])

#         for telemetry_id, values in data.items():
#             for entry in values:
#                 csv_writer.writerow([telemetry_id, entry.get("ts"), entry.get("value")])

#     print("✅ Data saved to telemetry_data.csv")
# else:
#     print(f"❌ API Request Failed: {response.status_code}")
#     print(response.text)
