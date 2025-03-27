import requests
import json
import csv

# AchtBytes API URL
url = "https://iot.achtbytes.com/copc/api/devices/95ddf841-f45b-44fb-94ac-d41ca67a091d/assets/ace015b4-1ecf-43c8-80b0-c5e3da2390f5/telemetry/timeline?telemetryIds=PDI_2_1&telemetryIds=PDI_2_2&telemetryIds=PDI_2_3&fromDate=2025-02-03T20%3A25%3A33.095Z&toDate=2025-03-10T20%3A25%3A32Z"

# Replace with your actual Bearer token
bearer_token = "eyJhbGciOiJSUzI1NiIsImtpZCI6IllFYmRpZUNYQnVZYmlHVkZKb1c2TWFGdjFIeE9jamhnR2Fxcm45dnl6bWciLCJ0eXAiOiJKV1QifQ.eyJhdWQiOiIwZTM5ZGNjMi0zOWM5LTRiMGMtOTk5Zi01Mzg1ZWI4OTYxYjgiLCJpc3MiOiJodHRwczovL3N0ZWdvY29ubmVjdGV1d3Byb2QuYjJjbG9naW4uY29tLzg5MTA2NmNiLTlmZmQtNGY4NS1hOWQ2LWRlNzVkMDM3M2VhNS92Mi4wLyIsImV4cCI6MTc0MTY0MDczMCwibmJmIjoxNzQxNjM3MTMwLCJzdWIiOiI5ZmQ0ZjgyYS0yMDgxLTQ0NzItYjUxNi1kNDNhZjUwYzkxZGYiLCJvaWQiOiI5ZmQ0ZjgyYS0yMDgxLTQ0NzItYjUxNi1kNDNhZjUwYzkxZGYiLCJlbWFpbCI6InZ0bjk2NDkyQHVnYS5lZHUiLCJuYW1lIjoiVmljdCBOZ3V5ZW4iLCJnaXZlbl9uYW1lIjoiVmljdCBOZ3V5ZW4iLCJmYW1pbHlfbmFtZSI6IlZpY3QgTmd1eWVuIiwidGlkIjoiODkxMDY2Y2ItOWZmZC00Zjg1LWE5ZDYtZGU3NWQwMzczZWE1Iiwibm9uY2UiOiIwMTk1ODFhOS01NDJmLTc4YTYtOTVlMC1hNmNjYTQ3YmU5MTciLCJzY3AiOiJhcGktYWNjZXNzIiwiYXpwIjoiMGUzOWRjYzItMzljOS00YjBjLTk5OWYtNTM4NWViODk2MWI4IiwidmVyIjoiMS4wIiwiaWF0IjoxNzQxNjM3MTMwfQ.HEfL3xpldDjBR4x_NiBc-90oXgmpo_vcR9Okr_g-zxk4A1WOJXMixGICVPrr1oFUUIR3JTN_eGqKauPqVLNKvlRlLRubP2nwdQ8D3DZqYZfPqhupe4HhNX4VZguwjNiblHT0CIPfTEJiMxpSbaBawjl_px_hJC_UIidFXX9-EpoqkfncpMS1R97QEj8IAQf0k_0N3lZEZm0vAPRYpFhfxmMRS7s6t49uNq45nv8EB4K-U26NSGp6CufQHk5EP1iX7mnHgJq8GAAnaF8x8hXdIlyVEroIHPNuJlsB8uRb1u9YD2uW0Mo0uSaCh6zLZzLK8l37-1bNSP1E-xhvEjcBZg"

# Headers for authentication
headers = {
    "Authorization": f"Bearer {bearer_token}",
    "Accept": "application/json"
}

# Make the API request
response = requests.get(url, headers=headers)

# Check if request was successful
if response.status_code == 200:
    data = response.json()

    # Save JSON data
    json_filename = "telemetry_data.json"
    with open(json_filename, "w") as json_file:
        json.dump(data, json_file, indent=4)
    print(f"Data successfully saved to {json_filename}")

    # Convert JSON to CSV
    csv_filename = "telemetry_data.csv"
    with open(csv_filename, "w", newline="") as csv_file:
        csv_writer = csv.writer(csv_file)
        
        # Write header row
        csv_writer.writerow(["telemetry_id", "timestamp", "value"])

        # Process JSON structure
        for telemetry_id, values in data.items():
            for entry in values:
                csv_writer.writerow([telemetry_id, entry.get("ts"), entry.get("value")])

    print(f"Data successfully saved to {csv_filename}")

else:
    print(f"Failed to retrieve data. HTTP Status Code: {response.status_code}")
    print(response.text)
