import json
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# AchtBytes Login Credentials (REPLACE THESE)
EMAIL = "vtn96492@uga.edu"
PASSWORD = "Capstone25!"

# Set up Chrome options and merge logging preferences
chrome_options = Options()
# chrome_options.add_argument("--headless")  # Uncomment if you want headless mode
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--remote-debugging-port=9222")
chrome_options.set_capability("goog:loggingPrefs", {"performance": "ALL"})

# Path to your ChromeDriver (modify if needed)
service = Service("/usr/local/bin/chromedriver")  # Change this path if necessary
driver = webdriver.Chrome(service=service, options=chrome_options)

# Open AchtBytes login page
driver.get("https://iot.achtbytes.com/copc/tenant")
time.sleep(15)  # Wait for the page to load

# Log in to AchtBytes
driver.find_element(By.ID, "signInName").send_keys(EMAIL)
driver.find_element(By.ID, "password").send_keys(PASSWORD + Keys.RETURN)
time.sleep(15)  # Wait for login to complete

# Click the assets button
driver.find_element(By.ID, "nav-item-assets-overview").click()
time.sleep(5)

# XPath for online asset cards
cards_xpath = "//a[contains(@class, 'overview-link') and .//span[text()='Online']]"

# Retrieve the number of online asset cards
cards = driver.find_elements(By.XPATH, cards_xpath)
num_cards = len(cards)
print(f"Found {num_cards} online asset card(s).")

bearer_tokens = []
telemetry_requests = {}

# Loop through each card by index and re-locate it each time to avoid stale references
for i in range(num_cards):
    try:
        # Wait until the card is clickable and re-find it
        card = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, f"({cards_xpath})[{i+1}]"))
        )
        card.click()
        print(f"\nClicked on card {i+1}/{num_cards}.")

        # Allow some time for network requests to occur
        time.sleep(10)

        # Retrieve performance logs from Chrome
        logs = driver.get_log("performance")
        for entry in logs:
            log_entry = json.loads(entry["message"])["message"]
            if log_entry.get("method") == "Network.requestWillBeSent":
                request = log_entry.get("params", {}).get("request", {})
                headers = request.get("headers", {})
                url = request.get("url", "")
                token = None
                # Capture Bearer token if present
                if "Authorization" in headers and "Bearer" in headers["Authorization"]:
                    token = headers["Authorization"].split("Bearer ")[1]
                    bearer_tokens.append(token)
                    print(f"🔑 Bearer Token Captured: {token}")
                # Capture telemetry request URL if applicable
                if "telemetry" in url and token:
                    telemetry_requests[url] = token
                    print(f"📡 Telemetry Request Captured: {url} → Token: {token}")

        print(f"✅ Captured {len(telemetry_requests)} Telemetry Requests so far.")
        print(f"✅ Captured {len(bearer_tokens)} Bearer Tokens so far.")

        # Navigate back to assets overview before processing the next card
        driver.find_element(By.ID, "nav-item-assets-overview").click()
        time.sleep(5)

    except Exception as e:
        print(f"Error processing card {i+1}: {e}")

time.sleep(10)
driver.quit()

import pandas as pd

# After processing all cards and capturing telemetry_requests and bearer_tokens

if telemetry_requests:
    df_telemetry = pd.DataFrame(
        list(telemetry_requests.items()), 
        columns=["Telemetry URL", "Bearer Token"]
    )
    # Write telemetry requests to CSV
    df_telemetry.to_csv("telemetry_requests.csv", index=False)
    print("\nTelemetry Requests saved to telemetry_requests.csv")
else:
    print("\n❌ No telemetry requests captured.")

if bearer_tokens:
    # Deduplicate tokens if needed:
    unique_tokens = list(set(bearer_tokens))
    df_tokens = pd.DataFrame(unique_tokens, columns=["Bearer Token"])
    # Write tokens to CSV
    df_tokens.to_csv("bearer_tokens.csv", index=False)
    print("\nBearer Tokens saved to bearer_tokens.csv")
else:
    print("\n❌ No bearer tokens captured.")



# (Baby Bear) STEGO Elektrotechnik GmbH ESS 076 (0002010ABFDE)
# https://iot.achtbytes.com/copc/api/devices/95ddf841-f45b-44fb-94ac-d41ca67a091d/assets/f61f0a65-6157-4999-82c4-8fd3941d6b8a/telemetry/timeline?telemetryIds=PI_SSP_PDI32_MSDC32_Ampere_1&telemetryIds=PI_SSP_PDI32_MSDC32_Ampere_2&telemetryIds=PI_SSP_PDI32_MSDC32_Ampere_3&fromDate=2024-03-10T18%3A17%3A20.246Z&toDate=2025-03-10T18%3A17%3A18Z
# https://iot.achtbytes.com/copc/api/devices/95ddf841-f45b-44fb-94ac-d41ca67a091d/assets/f61f0a65-6157-4999-82c4-8fd3941d6b8a/telemetry?telemetryIds=PI_SSP_PDI32_MSDC32_Ampere_1&telemetryIds=PI_SSP_PDI32_MSDC32_Ampere_2&telemetryIds=PI_SSP_PDI32_MSDC32_Ampere_3&fromDate=2024-10-10T22%3A40%3A24.786Z&toDate=2025-01-05T12%3A51%3A31.691Z
# https://iot.achtbytes.com/copc/api/devices/95ddf841-f45b-44fb-94ac-d41ca67a091d/assets/f61f0a65-6157-4999-82c4-8fd3941d6b8a/telemetry/timeline?telemetryIds=PI_SSP_PDI32_MSDC32_Ampere_1&telemetryIds=PI_SSP_PDI32_MSDC32_Ampere_2&telemetryIds=PI_SSP_PDI32_MSDC32_Ampere_3&fromDate=2024-03-10T18%3A17%3A20.246Z&toDate=2025-03-10T18%3A17%3A18Z
# https://iot.achtbytes.com/copc/api/devices/95ddf841-f45b-44fb-94ac-d41ca67a091d/assets/f61f0a65-6157-4999-82c4-8fd3941d6b8a/telemetry?telemetryIds=PI_SSP_PDI32_MSDC32_Ampere_1&telemetryIds=PI_SSP_PDI32_MSDC32_Ampere_2&telemetryIds=PI_SSP_PDI32_MSDC32_Ampere_3&fromDate=2024-10-10T22%3A40%3A24.786Z&toDate=2025-01-05T12%3A51%3A31.691Z
# 
# 
# 
# 
# 
# 
# 
# 
# 
# 
# 
# 
# 
# 
# 
# 
