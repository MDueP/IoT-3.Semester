from datetime import datetime, timedelta
import json
import re
import MySQLdb.cursors
import paho.mqtt.client as mqtt
from io import BytesIO
import numpy as np
from matplotlib.patches import Circle
import matplotlib.pyplot as plt
import matplotlib.gridspec
from flask import Flask, request, redirect, url_for, session, render_template, Response
from flask_mysqldb import MySQL
from flask_bcrypt import Bcrypt
import dotenv
import os
import matplotlib
matplotlib.use('Agg')

absolutepath = os.path.dirname(os.path.abspath(__file__))
os.chdir(absolutepath)
dotenv.load_dotenv()
ca_file = os.path.abspath('ca.crt')
cert_file = os.path.abspath('server.crt')
pkey_file = os.path.abspath('server.key')
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_APP_KEY")
bcrypt = Bcrypt(app)

app.config["MYSQL_HOST"] = os.getenv("MYSQL_HOST")
app.config["MYSQL_USER"] = os.getenv("MYSQL_USER")
app.config["MYSQL_PASSWORD"] = os.getenv("MYSQL_PASSWORD")
app.config["MYSQL_DB"] = os.getenv("MYSQL_DB")
mysql = MySQL(app)

cache_sensor = {"puls": [], "batteri_procent": []}


def fetch_data():
    last_time = datetime.now() - timedelta(minutes=5)
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute(
        "SELECT gyro_x, gyro_y, gyro_z FROM gyrodata WHERE timestamp > %s", (last_time,))
    data = cursor.fetchall()
    return [{"GyroX": row["gyro_x"], "GyroY": row["gyro_y"], "GyroZ": row["gyro_z"]} for row in data]


def tjek_for_fald(data):
    gyro_x = [entry["GyroX"] for entry in data]
    gyro_y = [entry["GyroY"] for entry in data]
    gyro_z = [entry["GyroZ"] for entry in data]

    mean_x = np.mean(gyro_x)
    mean_y = np.mean(gyro_y)
    mean_z = np.mean(gyro_z)

    std_x = np.std(gyro_x)
    std_y = np.std(gyro_y)
    std_z = np.std(gyro_z)

    threshold_std = 20
    threshold_mean = 1.0
    if std_x > threshold_std or std_y > threshold_std or std_z > threshold_std:
        return True
    if abs(mean_x) > threshold_mean or abs(mean_y) > threshold_mean or abs(mean_z) > threshold_mean:
        return True
    return False


def drop_data():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("DELETE FROM gyrodata WHERE timestamp < %s",
                   (datetime.now() - timedelta(minutes=5),))
    mysql.connection.commit()


def mqtt_setup(app):
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.connect("localhost", 1883)
    client.subscribe("iot3")

    def message(client, data, msg):
        with app.app_context():
            try:
                sensordata = json.loads(msg.payload.decode())
                batteriprocent = sensordata["BatteryPercentage"]
                Puls = sensordata["HeartRate"]
                gyro_data = sensordata["Gyroscope"]
                gyro_x = gyro_data["GyroX"]
                gyro_y = gyro_data["GyroY"]
                gyro_z = gyro_data["GyroZ"]
                cache_sensor["puls"].append(Puls)
                cache_sensor["batteri_procent"].append(batteriprocent)

                if len(cache_sensor["puls"]) > 10:
                    cache_sensor["puls"].pop(0)
                if len(cache_sensor["batteri_procent"]) > 10:
                    cache_sensor["batteri_procent"].pop(0)
                cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
                cursor.execute(
                    "INSERT INTO gyrodata (gyro_x, gyro_y, gyro_z) VALUES (%s, %s, %s)",
                    (gyro_x, gyro_y, gyro_z)
                )
                mysql.connection.commit()
            except Exception as e:
                print(f"Error processing message: {e}")
    client.on_message = message
    client.loop_start()


mqtt_setup(app)


@app.route("/graphplot", methods=["GET", "POST"])
def datagrafer():
    data = fetch_data()
    fald_opdaget = tjek_for_fald(data)
    gyro_x = [entry["GyroX"] for entry in data]
    Timestamps = [(datetime.now() + timedelta(minutes=i)).strftime("%H:%M")
                  for i in range(len(gyro_x))]
    global cache_sensor

    hjerterytme = cache_sensor["puls"]
    batteri = cache_sensor["batteri_procent"]

    fig, ax = plt.subplots(3, 1, figsize=(10, 8), constrained_layout=True)

    spec = matplotlib.gridspec.GridSpec(
        3, 2, width_ratios=[1, 1], height_ratios=[1, 1, 1])
    ax[0] = fig.add_subplot(spec[0, 0])

    if gyro_x:
        ax[0].plot(Timestamps, gyro_x, label="Gyro X")
    ax[0].legend()
    ax[0].set_title("Gyroscope Data")
    ax[0].set_xlabel("Time")
    ax[0].set_ylabel("Value")
    ax[0].set_xticks([])
    ax[0].grid()

    ax_circle = fig.add_subplot(spec[0, 1])

    circle_color = "red" if fald_opdaget else "green"
    ax_circle.add_patch(Circle((0.5, 0.5), 0.4, color=circle_color))
    ax_circle.text(0.5, -0.2, "Fald opdaget" if fald_opdaget else "Intet fald",
                   color=circle_color, fontsize=10, ha="center")
    ax_circle.set_xticks([])
    ax_circle.set_xlim(0, 1)
    ax_circle.set_ylim(0, 1)
    ax_circle.axis("off")

    if hjerterytme:
        ax[1].plot(Timestamps[:len(hjerterytme)],
                   hjerterytme, label="Puls", color="red")
    ax[1].set_title("Hjerterytme")
    ax[1].set_xlabel("Tid")
    ax[1].set_ylabel("BPM")
    ax[1].grid()
    ax[1].legend()

    if batteri:
        ax[2].plot(Timestamps[:len(batteri)], batteri,
                   label="Batteriprocent", color="green")
    ax[2].set_title("Batteri")
    ax[2].set_xlabel("Tid")
    ax[2].set_ylabel("Batteri %")
    ax[2].grid()
    ax[2].legend()

    buf = BytesIO()
    fig.tight_layout()
    fig.savefig(buf, format="png")
    plt.close(fig)
    buf.seek(0)

    drop_data()

    return Response(buf, mimetype='image/png')


@app.route('/graph', methods=['GET', 'POST'])
def graph():
    return render_template('graph.html')


@app.route('/', methods=['GET', 'POST'])
def login():
    msg = ''
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form:
        username = request.form['username']
        password = request.form['password']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute(
            'SELECT * FROM iot3webapp.logindb WHERE username = %s', (username,))
        account = cursor.fetchone()
        if account and bcrypt.check_password_hash(account['password'], password):
            session['loggedin'] = True
            session['id'] = account['id']
            session['username'] = account['username']
            return render_template('home.html', msg=msg)
        else:
            msg = 'Incorrect Username or Password'
    return render_template('login.html', msg=msg)


@app.route('/home')
def home():
    if 'loggedin' in session:
        return render_template('home.html', username=session['username'])
    return redirect(url_for('login'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    msg = ''
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form:
        username = request.form['username']
        password = request.form['password']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute(
            'SELECT * FROM iot3webapp.logindb WHERE username = %s', (username,))
        account = cursor.fetchone()

        if account:
            msg = 'Account already exists'
        elif not re.match(r'[A-Za-z0-9]+', username):
            msg = 'Username must contain only characters and numbers'
        elif not username or not password:
            msg = 'Please fill out all the fields'
        else:
            hashed_password = bcrypt.generate_password_hash(
                password).decode('utf-8')
            cursor.execute('INSERT INTO iot3webapp.logindb VALUES (NULL, %s, %s)',
                           (username, hashed_password,))
            mysql.connection.commit()
            msg = 'Successfully registered'
        return render_template('login.html', msg=msg)
    elif request.method == 'POST':
        msg = 'Please fill out all the fields '
    return render_template('register.html', msg=msg)


@app.route('/logout')
def logout():
    session.pop('loggedin', None)
    session.pop('id', None)
    session.pop('username', None)
    return redirect(url_for('login'))


app.run(host="0.0.0.0", ssl_context=(cert_file, pkey_file))
