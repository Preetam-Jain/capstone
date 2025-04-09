import json
import uuid
import threading
import time
import requests
import pandas as pd
import io
import os

from flask import Blueprint, jsonify, request, render_template
from flask_mail import Message
from board.mail import mail
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from xhtml2pdf import pisa

bp = Blueprint("pages", __name__)

############################################################
# 1) GLOBAL SCHEDULER
############################################################
scheduler = BackgroundScheduler()

############################################################
# 2) FILE-BASED SUBSCRIBER PERSISTENCE
############################################################
SUBSCRIBERS_FILE = "subscribers.txt"

def load_subscribers():
    """Load emails from subscribers.txt, one email per line."""
    if not os.path.exists(SUBSCRIBERS_FILE):
        return []
    with open(SUBSCRIBERS_FILE, "r") as f:
        lines = [line.strip() for line in f.readlines()]
        return [email for email in lines if email]

def save_subscribers(emails_list):
    """Overwrite subscribers.txt with the current list of emails."""
    with open(SUBSCRIBERS_FILE, "w") as f:
        for email in emails_list:
            f.write(email + "\n")

emails = load_subscribers()  # In-memory + persisted on disk
SCRAPE_JOBS = {}

############################################################
# 3) SCRAPE / TELEMETRY LOGIC
############################################################
def scrape_and_get_telemetry():
    """
    Logs into AchtBytes, scrapes 'Online' assets, captures telemetry requests,
    then queries those telemetry endpoints. Returns dict with 'telemetry_data'.
    """
    import chromedriver_autoinstaller
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC

    chromedriver_autoinstaller.install()

    EMAIL = "vtn96492@uga.edu"
    PASSWORD = "Capstone25!"

    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--remote-debugging-port=9222")
    chrome_options.set_capability("goog:loggingPrefs", {"performance": "ALL"})

    driver = webdriver.Chrome(options=chrome_options)
    try:
        driver.get("https://iot.achtbytes.com/copc/tenant")
        time.sleep(15)

        # Log in
        driver.find_element(By.ID, "signInName").send_keys(EMAIL)
        driver.find_element(By.ID, "password").send_keys(PASSWORD + Keys.RETURN)
        time.sleep(20)

        # Go to assets overview
        driver.find_element(By.ID, "nav-item-assets-overview").click()
        time.sleep(5)

        # Find 'Online' cards
        cards_xpath = "//a[contains(@class, 'overview-link') and .//span[text()='Online']]"
        cards = driver.find_elements(By.XPATH, cards_xpath)
        print(f"[SCRAPE] Found {len(cards)} online asset card(s).")

        bearer_tokens = []
        telemetry_requests = {}

        # For each card, capture bearer tokens + telemetry endpoints
        for i in range(len(cards)):
            try:
                card = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, f"({cards_xpath})[{i+1}]"))
                )
                card.click()
                time.sleep(5)

                logs = driver.get_log("performance")
                for entry in logs:
                    log_json = json.loads(entry["message"])["message"]
                    if log_json.get("method") == "Network.requestWillBeSent":
                        req = log_json.get("params", {}).get("request", {})
                        headers = req.get("headers", {})
                        url = req.get("url", "")
                        if "Authorization" in headers and "Bearer" in headers["Authorization"]:
                            token = headers["Authorization"].split("Bearer ")[1]
                            bearer_tokens.append(token)
                            if "telemetry" in url:
                                telemetry_requests[url] = token

                # Back to overview
                driver.find_element(By.ID, "nav-item-assets-overview").click()
                time.sleep(5)

            except Exception as e:
                print(f"[SCRAPE] Error processing card {i+1}: {e}")

        time.sleep(5)
        driver.quit()

        # Query telemetry endpoints
        telemetry_data = {}
        for url, token in telemetry_requests.items():
            headers = {"Authorization": f"Bearer {token}"}
            try:
                resp = requests.get(url, headers=headers)
                resp.raise_for_status()
                telemetry_data[url] = resp.json()
            except Exception as ex:
                telemetry_data[url] = {"error": str(ex)}
        print("got here")
        with open("telemetry_output.json", "w") as f:
            json.dump(telemetry_data, f, indent=4)

        return {
            "telemetry_requests": telemetry_requests,
            "unique_tokens": list(set(bearer_tokens)),
            "telemetry_data": telemetry_data
        }
    finally:
        driver.quit()

def run_scrape_job(job_id):
    """
    For the /start_scrape route. Kicks off a thread to do scraping.
    """
    SCRAPE_JOBS[job_id]["status"] = "in progress"
    try:
        data = scrape_and_get_telemetry()
        SCRAPE_JOBS[job_id]["status"] = "complete"
        SCRAPE_JOBS[job_id]["result"] = data
    except Exception as e:
        SCRAPE_JOBS[job_id]["status"] = "error"
        SCRAPE_JOBS[job_id]["error"] = str(e)

############################################################
# 4) TWO-CHART SCREENSHOT LOGIC
############################################################
from xhtml2pdf import pisa

def parse_all_endpoints_no_duplicates(telemetry_data):
    """
    Mimics the JS parseAllEndpointsNoDuplicates logic:
      - For each endpoint, extract the assetID from the URL.
      - Take only the first items list (assumed to have the relevant values).
      - If no name is given in the response, extract the first telemetryId from the URL.
      - Build a composite key using "assetID_itemName".
      - Filter out data points with value 0 or -2.
    """
    import re
    import datetime

    series_data = {}
    for url, content in telemetry_data.items():
        if not content:
            continue

        # Extract assetID from URL
        asset_match = re.search(r"/assets/([^/]+)", url)
        assetID = asset_match.group(1) if asset_match else "UnknownAsset"

        # Determine top-level items list
        if isinstance(content, dict) and "items" in content and isinstance(content["items"], list):
            topLevelItems = content["items"]
        elif isinstance(content, list):
            topLevelItems = content
        else:
            continue

        if topLevelItems and len(topLevelItems) > 0:
            # Process only the first items list from this endpoint
            item = topLevelItems[0]
            # Get the telemetry name: use item.name if available; otherwise extract from URL
            itemName = item.get("name")
            if not itemName:
                telemetry_match = re.search(r"telemetryIds=([^&]+)", url)
                itemName = telemetry_match.group(1).lower() if telemetry_match else "unknown"
            compositeKey = assetID + "_" + itemName

            subitems = item.get("items", [])
            if not isinstance(subitems, list):
                continue

            data_points = []
            for dp in subitems:
                try:
                    val = float(dp.get("average"))
                    ts = dp.get("timestamp")
                    if not ts:
                        continue
                    # Remove trailing 'Z' if present and convert timestamp
                    ts = ts.replace("Z", "")
                    dt = datetime.datetime.fromisoformat(ts)
                    # Filter out irrelevant values
                    if val == 0 or val == -2:
                        continue
                    data_points.append({"x": dt.isoformat(), "y": val})
                except Exception as e:
                    continue
            data_points.sort(key=lambda d: d["x"])
            if compositeKey not in series_data:
                series_data[compositeKey] = data_points
    return series_data

def partition_currents_and_temps(series_data):
    currents = {}
    temps = {}
    for name, points in series_data.items():
        lower = name.lower()
        if "ampere" in lower:
            currents[name] = points
        elif "pdi" in lower:
            temps[name] = points
    return currents, temps

def _render_single_chart(chart_title, series_json, y_label, chart_type):
    """
    Renders a single chart using Chart.js in headless Chrome. 
    Assigns custom colors based on insertion order:
      - ampere (currents): 
          index=0 => Auxiliary (blue), 
          index=1 => Traffic (red), 
          index=2 => Total (orange)
      - temperature: 
          index=0 => Temperature (blue), 
          index=1 => Humidity (red)
      - extras => gray
    """
    import tempfile
    import time
    import os
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    import chromedriver_autoinstaller

    chromedriver_autoinstaller.install()

    html_content = f"""
    <html>
    <head>
      <meta charset="utf-8" />
      <title>{chart_title}</title>
      <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
      <script src="https://cdn.jsdelivr.net/npm/luxon@3/build/global/luxon.min.js"></script>
      <script src="https://cdn.jsdelivr.net/npm/chartjs-adapter-luxon@1"></script>
      <style>
        body {{
          margin: 20px;
          font-family: Arial, sans-serif;
        }}
        #myChart {{
          width: 800px;
          height: 600px;
        }}
      </style>
    </head>
    <body>
      <h2>{chart_title}</h2>
      <canvas id="myChart" width="800" height="600"></canvas>
      <script>
        const dataObj = {series_json};

        let datasets = [];
        const keys = Object.keys(dataObj);  // preserve insertion order

        keys.forEach((key, index) => {{
          // Convert the data points
          let points = dataObj[key].map(pt => ({{ x: pt.x, y: pt.y }}));

          // Scale if needed
          if ("ampere" === "{chart_type}") {{
            // currents => divide by 100
            points = points.map(o => ({{ x: o.x, y: o.y / 100 }}));
          }} else if ("temperature" === "{chart_type}") {{
            // temperature => divide by 10
            points = points.map(o => ({{ x: o.x, y: o.y / 10 }}));
          }}

          let newLabel = key;
          let color = "#888"; // fallback gray

          if ("ampere" === "{chart_type}") {{
            // Use custom labeling & colors
            if (index === 0) {{
              newLabel = "Auxiliary Current (A)";
              color = "#36A2EB"; // Blue
            }} else if (index === 1) {{
              newLabel = "Traffic Controller Current (A)";
              color = "#FF6384"; // Red
            }} else if (index === 2) {{
              newLabel = "Total Current (A)";
              color = "#FF9F40"; // Orange
            }}
          }} else if ("temperature" === "{chart_type}") {{
            if (index === 0) {{
              newLabel = "Temperature (°F)";
              color = "#36A2EB"; // Blue
            }} else if (index === 1) {{
              newLabel = "Humidity (%)";
              color = "#FF6384"; // Red
            }}
          }}

          datasets.push({{
            label: newLabel,
            data: points,
            borderWidth: 2,
            fill: false,
            borderColor: color
          }});
        }});

        const ctx = document.getElementById('myChart').getContext('2d');
        new Chart(ctx, {{
          type: 'line',
          data: {{ datasets }},
          options: {{
            scales: {{
              x: {{
                type: 'time',
                time: {{ tooltipFormat: 'll HH:mm' }},
                title: {{ display: true, text: 'Timestamp' }}
              }},
              y: {{
                title: {{ display: true, text: '{y_label}' }}
              }}
            }}
          }}
        }});
      </script>
    </body>
    </html>
    """

    import tempfile
    temp_html_file = tempfile.NamedTemporaryFile(delete=False, suffix=".html")
    temp_html_file.write(html_content.encode("utf-8"))
    temp_html_file.close()
    html_path = temp_html_file.name

    screenshot_bytes = None
    try:
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")

        driver = webdriver.Chrome(options=chrome_options)
        driver.set_window_size(1000, 800)
        driver.get("file://" + html_path)
        time.sleep(3)

        full_height = driver.execute_script("return document.body.scrollHeight")
        driver.set_window_size(1000, full_height + 50)
        time.sleep(1)

        screenshot_bytes = driver.get_screenshot_as_png()
        driver.quit()
    finally:
        os.remove(html_path)

    return screenshot_bytes

def generate_two_charts_images(telemetry_data):
    """
    Partitions the telemetry data into currents and temperatures using the new parsing logic,
    then renders them as two PNG images.
    """
    series_data = parse_all_endpoints_no_duplicates(telemetry_data)
    currents, temps = partition_currents_and_temps(series_data)

    import json
    currents_json = json.dumps(currents)
    temps_json = json.dumps(temps)

    c_png = _render_single_chart("Currents (Ampere)", currents_json, "Current (A)", "ampere")
    t_png = _render_single_chart("Temperatures (°F)", temps_json, "Temperature (°F)", "temperature")
    return c_png, t_png

############################################################
# 5) WEEKLY JOB -> SEND EMAILS TO ALL
############################################################
def sendWeeklyUpdateAll(app):
    """
    APScheduler calls this with `app` as an argument.
    We push an app context, perform scraping, generate chart screenshots,
    and email each subscriber the weekly report.
    """
    with app.app_context():
        print("[JOB] sendWeeklyUpdateAll triggered")
        data = scrape_and_get_telemetry()
        telemetry = data.get("telemetry_data", {})

        c_png, t_png = generate_two_charts_images(telemetry)

        for e in emails:
            _sendSingleUserReport(e, c_png, t_png)

def _sendSingleUserReport(email, c_png, t_png):
    subject = "Weekly AchtBytes Telemetry Report"
    body = (
        "Hello,\n\n"
        "Please find attached a PDF summary plus two chart snapshots:\n"
        "1) Currents (Ampere)\n"
        "2) Temperatures (°F)\n\n"
        "Regards,\nCapstone - Traffic Monitoring Dashboard"
    )
    msg = Message(subject=subject, sender="capstonetestingtester@gmail.com", recipients=[email])
    msg.body = body

    # Minimal PDF
    pdf_html = """
    <html>
      <head>
        <style>
          body { font-family: Arial, sans-serif; margin: 20px; }
          h2 { color: #333; }
        </style>
      </head>
      <body>
        <h2>Weekly AchtBytes Telemetry Report</h2>
        <p>Attached are two images: Currents and Temperatures charts.</p>
      </body>
    </html>
    """
    pdf_buffer = io.BytesIO()
    pisa.CreatePDF(io.StringIO(pdf_html), dest=pdf_buffer)
    pdf_buffer.seek(0)

    msg.attach("weekly_report.pdf", "application/pdf", pdf_buffer.read())

    if c_png:
        msg.attach("currents_chart.png", "image/png", c_png)
    if t_png:
        msg.attach("temperatures_chart.png", "image/png", t_png)

    try:
        mail.send(msg)
        print(f"[EMAIL] Sent to {email}")
    except Exception as ex:
        print(f"[EMAIL] Failed for {email}: {ex}")

############################################################
# 6) INIT SCHEDULER
############################################################
def init_scheduler(app):
    """
    Starts the scheduler (if not running) and schedules sendWeeklyUpdateAll
    to run periodically (every 10 minutes in this example).
    """
    if not scheduler.running:
        scheduler.start()

    scheduler.add_job(
        sendWeeklyUpdateAll,
        trigger=CronTrigger(minute='*/10'),
        args=[app],
        max_instances=1
    )

############################################################
# 7) FLASK ROUTES
############################################################
@bp.route("/")
def home():
    return render_template("pages/home.html")

@bp.route("/about")
def about():
    return render_template("pages/about.html")

@bp.route("/start_scrape", methods=["POST"])
def start_scrape():
    job_id = str(uuid.uuid4())
    SCRAPE_JOBS[job_id] = {"status": "pending", "result": None, "error": None}

    thread = threading.Thread(target=run_scrape_job, args=(job_id,))
    thread.start()
    return jsonify({"job_id": job_id})

@bp.route("/scrape_status")
def scrape_status():
    job_id = request.args.get("job_id")
    if not job_id or job_id not in SCRAPE_JOBS:
        return jsonify({"error": "Invalid or missing job_id"}), 400

    job = SCRAPE_JOBS[job_id]
    return jsonify({
        "status": job["status"],
        "result": job["result"],
        "error": job["error"]
    })

@bp.route("/dashboard")
def dashboard():
    return render_template("pages/dashboard.html")

@bp.route("/carbon-emissions")
def carbon_emissions():
    return render_template("pages/carbon_emissions.html")

@bp.route('/subscribe', methods=['GET', 'POST'])
def subscribe():
    if request.method == 'POST':
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        email = request.form.get('email')

        if not first_name or not last_name or not email:
            return render_template('pages/subscribe.html', error="All fields are required.")

        if email not in emails:
            emails.append(email)
            save_subscribers(emails)

            # Confirmation email
            subject = "Subscription Confirmed"
            body = f"Hello {first_name},\n\nYou've been added to the weekly reports."
            msg = Message(subject=subject, sender="capstonetestingtester@gmail.com", recipients=[email])
            msg.body = body

            try:
                mail.send(msg)
                return render_template('pages/subscribe.html', success="Subscribed successfully!")
            except Exception as e:
                return render_template('pages/subscribe.html', error=f"Failed to send email: {str(e)}")
        else:
            return render_template('pages/subscribe.html', error="Email already subscribed")
    return render_template('pages/subscribe.html')

@bp.route('/fetch-data', methods=['GET'])
def fetch_data():
    url = "https://testapi.io/api/aam08331/Testapi"
    try:
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        return jsonify(r.json())
    except requests.exceptions.RequestException as e:
        return jsonify({"error": str(e)}), 500

@bp.route('/send-data', methods=['POST'])
def send_data():
    url = "https://testapi.io/api/aam08331/Testapi"
    data = {"test": "test", "num": 1}
    try:
        r = requests.post(url, json=data, timeout=5)
        r.raise_for_status()
        return jsonify(r.json())
    except requests.exceptions.RequestException as e:
        return jsonify({"error": str(e)}), 500

@bp.route('/carbon/<int:kiloWattHrs>', methods=['GET'])
def carbon(kiloWattHrs):
    tonToPounds = 2204.6
    actual = (3.94 * 10e-4) * tonToPounds * kiloWattHrs
    return jsonify({"result": actual})
