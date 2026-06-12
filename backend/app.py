from flask import Flask, render_template, request, redirect, session
import mysql.connector
import pickle
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__, template_folder="../frontend")
app.secret_key = "secret123"

# ------------------ DB CONNECTION ------------------
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="Rajitha123",
    database="students_data"
)

# 🔥 FIX: dictionary + buffered cursor
cursor = db.cursor(buffered=True, dictionary=True)

# ------------------ CREATE TABLE ------------------
def init_db():
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS predicted_students (
        id INT AUTO_INCREMENT PRIMARY KEY,
        username VARCHAR(50),
        password VARCHAR(255),

        age INT,
        gender INT,
        screen FLOAT,
        social FLOAT,
        entertainment FLOAT,
        study FLOAT,
        sleep FLOAT,

        anxiety VARCHAR(20),
        depression VARCHAR(20),
        stress VARCHAR(20),

        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    db.commit()

init_db()

# ------------------ LOAD MODEL ------------------
models = pickle.load(open("logistic_models.pkl", "rb"))
scaler = pickle.load(open("scaler.pkl", "rb"))

labels = ["Low", "Moderate", "High"]

# ------------------ ROUTES ------------------

@app.route('/')
def login():
    return render_template("login.html")

@app.route('/register_page')
def register_page():
    return render_template("register.html")

# -------- REGISTER --------
@app.route('/register', methods=['POST'])
def register():
    username = request.form['username']
    password = request.form['password']

    hashed = generate_password_hash(password)

    cursor.execute("SELECT * FROM predicted_students WHERE username=%s", (username,))
    user = cursor.fetchone()

    if user:
        return "User already exists ❌"

    cursor.execute("""
    INSERT INTO predicted_students (username, password)
    VALUES (%s, %s)
    """, (username, hashed))

    db.commit()
    return redirect('/')

# -------- LOGIN --------
@app.route('/login', methods=['POST'])
def do_login():
    username = request.form['username']
    password = request.form['password']

    cursor.execute("SELECT * FROM predicted_students WHERE username=%s", (username,))
    user = cursor.fetchone()

    if user and check_password_hash(user["password"], password):
        session['user'] = username
        return redirect('/dashboard')
    else:
        return "Invalid Credentials ❌"

# -------- DASHBOARD --------
@app.route('/dashboard')
def dashboard():
    if 'user' in session:
        return render_template("dashboard.html")
    return redirect('/')

# -------- LOGOUT --------
@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect('/')

# -------- PREDICT --------
@app.route('/predict', methods=['POST'])
def predict():
    if 'user' not in session:
        return redirect('/')

    username = session['user']

    age = float(request.form['age'])
    gender = float(request.form['gender'])
    screen = float(request.form['screen'])
    social = float(request.form['social'])
    entertainment = float(request.form['entertainment'])
    study = float(request.form['study'])
    sleep = float(request.form['sleep'])

    data = scaler.transform([[age, gender, screen, social, entertainment, study, sleep]])

    anxiety = labels[models["anxiety_class"].predict(data)[0]]
    depression = labels[models["depression_class"].predict(data)[0]]
    stress = labels[models["stress_class"].predict(data)[0]]

    cursor.execute("""
    INSERT INTO predicted_students
    (username, age, gender, screen, social, entertainment, study, sleep, anxiety, depression, stress)
    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """, (username, age, gender, screen, social, entertainment, study, sleep, anxiety, depression, stress))

    db.commit()

    return render_template("dashboard.html",
        anxiety=anxiety,
        depression=depression,
        stress=stress
    )

# -------- HISTORY --------
@app.route('/history')
def history():
    # For testing - remove login requirement
    if 'user' not in session:
        # Return empty data if not logged in
        return render_template("history.html", data=[])

    cursor.execute("""
    SELECT created_at, age, screen, study, sleep, anxiety, depression, stress
    FROM predicted_students
    WHERE username=%s AND anxiety IS NOT NULL
    ORDER BY created_at DESC
    """, (session['user'],))

    data = cursor.fetchall()

    return render_template("history.html", data=data)

# -------- ABOUT --------
@app.route('/about')
def about():
    return render_template("about.html")

# -------- CONTACT --------
@app.route('/contact')
def contact():
    return render_template("contact.html")

# ------------------ RUN ------------------
if __name__ == "__main__":
    app.run(debug=True)