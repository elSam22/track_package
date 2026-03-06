from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import logging
import csv

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

track_number = input("Enter the tracking number: ")
page = f"https://parcelsapp.com/fr/tracking/{track_number}"

options = Options()
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_experimental_option("useAutomationExtension", False)
options.add_argument("--window-position=10000,10000")
options.add_argument("--window-size=0,0")

driver = webdriver.Chrome(options=options)
driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
    "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
})

driver.get(page)
WebDriverWait(driver, 30).until(
    EC.presence_of_element_located((By.CSS_SELECTOR, "div.row.parcel"))
)

data = []
soup = BeautifulSoup(driver.page_source, "html.parser")
parcel = soup.find("div", class_="row parcel")
if parcel:
    logger.info("Parcel found")
    events = parcel.find("ul", class_="events").find_all("li", class_="event")
    logger.info(f"Found {len(events)} events for the parcel")
    for event in events:
        time_el = event.find("div", class_="event-time")
        content_el = event.find("div", class_="event-content")

        time = time_el.find("span").text.strip() if time_el and time_el.find("span") else None
        date = time_el.find("strong").text.strip() if time_el and time_el.find("strong") else None
        status = content_el.find("strong").text.strip() if content_el and content_el.find("strong") else None
        location_el = content_el.find("span", class_="location") if content_el else None
        location = location_el.text.strip() if location_el else None
        carrier_el = content_el.find("div", class_="carrier") if content_el else None
        carrier = carrier_el.text.strip() if carrier_el else None

        data.append({
            "track_number": track_number,
            "date": date,
            "time": time,
            "status": status,
            "location": location,
            "carrier": carrier
        })
else:
    logger.warning("No parcel information found on the page.")

logger.info(f"Extracted data: {data}")

with open(f"data/tracking_data_{track_number}.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=["track_number", "date", "time", "status", "location", "carrier"])
    writer.writeheader()
    writer.writerows(data)

logger.info(f"CSV file created: data/tracking_data_{track_number}.csv")

driver.quit()