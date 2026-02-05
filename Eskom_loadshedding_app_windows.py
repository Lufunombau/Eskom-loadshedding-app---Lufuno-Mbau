# ==================================================
# ESKOMSEPUSH – SINGLE FILE WINDOWS APP
# Streamlit + Auto Launcher
# ==================================================

import os
import sys
import json
import requests
import subprocess
from bs4 import BeautifulSoup
import pdfplumber

# ----------------------------------
# AUTO-LAUNCH STREAMLIT IF NEEDED
# ----------------------------------
if "streamlit" not in sys.argv[0]:
    subprocess.Popen([
        sys.executable,
        "-m", "streamlit",
        "run",
        os.path.abspath(__file__),
        "--server.headless=true"
    ])
    sys.exit()

# ----------------------------------
# STREAMLIT APP STARTS HERE
# ----------------------------------
import streamlit as st

ESKOM_URL = "https://www.eskom.co.za/distribution/customer-service/outages/load-shedding/"
RAW_DIR = "eskom_raw"
DATA_DIR = "eskom_data"

PROVINCES = [
    "Gauteng", "Western Cape", "KwaZulu-Natal",
    "Eastern Cape", "Free State", "Limpopo",
    "Mpumalanga", "North West", "Northern Cape"
]

os.makedirs(RAW_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

# ----------------------------------
# FETCH ESKOM SCHEDULES
# ----------------------------------
def fetch_eskom_data():
    response = requests.get(ESKOM_URL, timeout=20)
    soup = BeautifulSoup(response.text, "html.parser")

    pdf_links = []
    for a in soup.find_all("a", href=True):
        if a["href"].endswith(".pdf"):
            url = a["href"]
            if not url.startswith("http"):
                url = "https://www.eskom.co.za" + url
            pdf_links.append(url)

    for url in set(pdf_links):
        name = url.split("/")[-1]
        path = os.path.join(RAW_DIR, name)

        if not os.path.exists(path):
            r = requests.get(url, timeout=30)
            if r.status_code == 200:
                with open(path, "wb") as f:
                    f.write(r.content)

# ----------------------------------
# PARSE PDF → JSON
# ----------------------------------
def parse_pdfs():
    schedules = {}

    for file in os.listdir(RAW_DIR):
        if file.endswith(".pdf"):
            try:
                with pdfplumber.open(os.path.join(RAW_DIR, file)) as pdf:
                    for page in pdf.pages:
                        table = page.extract_table()
                        if not table or len(table) < 2:
                            continue
                        for row in table[1:]:
                            if row and row[0]:
                                schedules[row[0]] = row[1:]
            except:
                pass

    with open(os.path.join(DATA_DIR, "schedules.json"), "w") as f:
        json.dump(schedules, f, indent=2)

# ----------------------------------
# LOAD DATA
# ----------------------------------
def load_data():
    path = os.path.join(DATA_DIR, "schedules.json")
    if not os.path.exists(path):
        fetch_eskom_data()
        parse_pdfs()

    with open(path) as f:
        return json.load(f)

# ----------------------------------
# UI
# ----------------------------------
st.set_page_config(page_title="Eskom Loadshedding app", page_icon="⚡", layout="wide")

st.title("⚡ Eskom load shedding app – Windows App")
st.caption("Unofficial Eskom load shedding schedules")

if st.button("🔄 Refresh Eskom Data"):
    with st.spinner("Updating schedules..."):
        fetch_eskom_data()
        parse_pdfs()
    st.success("Data updated")

data = load_data()

if not data:
    st.warning("No schedules available")
    st.stop()

area = st.selectbox("🏘 Select Area", sorted(data.keys()))
stage = st.selectbox("🚦 Load Shedding Stage",
                     ["Stage 1", "Stage 2", "Stage 3", "Stage 4", "Stage 5", "Stage 6"])

st.subheader(f"⏰ {stage} Schedule")

times = data.get(area, [])
if times:
    for t in times:
        st.write("•", t)
else:
    st.info("No schedule available for this area")
