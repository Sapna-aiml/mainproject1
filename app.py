from flask import Flask, render_template, request, redirect, session
import sqlite3

app = Flask(__name__)
app.secret_key = "atm_secret"

# ---------- DATABASE ----------
def get_db():
    return sqlite3.connect("atm.db")

def setup_db():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        acc TEXT PRIMARY KEY,
        pin TEXT,
        balance INTEGER
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        acc TEXT,
        type TEXT,
        amount INTEGER,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cur.execute("INSERT OR IGNORE INTO users VALUES ('1234','1111',5000)")
    conn.commit()
    conn.close()

# ---------- ROUTES ----------

@app.route("/")
def home():
    return render_template("home.html")


@app.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        acc = request.form["acc"]
        pin = request.form["pin"]
        balance = int(request.form["balance"])

        conn = get_db()
        cur = conn.cursor()

        cur.execute("SELECT * FROM users WHERE acc=?", (acc,))
        if cur.fetchone():
            conn.close()
            return render_template("register.html", error="Account already exists")

        cur.execute("INSERT INTO users VALUES (?,?,?)", (acc, pin, balance))
        conn.commit()
        conn.close()

        return redirect("/signin")

    return render_template("register.html")


@app.route("/signin")
def signin():
    return render_template("login.html")


@app.route("/login", methods=["POST"])
def login():
    acc = request.form["acc"]
    pin = request.form["pin"]

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE acc=? AND pin=?", (acc, pin))
    user = cur.fetchone()
    conn.close()

    if user:
        session["acc"] = acc
        return redirect("/dashboard")
    else:
        return render_template("login.html", error="Invalid Account Number or PIN")

@app.route("/dashboard")
def dashboard():
    if "acc" not in session:
        return redirect("/")

    conn = get_db()
    cur = conn.cursor()

    # 1️⃣ Balance fetch
    cur.execute(
        "SELECT balance FROM users WHERE acc=?",
        (session["acc"],)
    )
    bal = cur.fetchone()[0]

    # 2️⃣ Transaction history fetch (IMPORTANT PART)
    cur.execute(
        "SELECT type, amount, timestamp FROM transactions WHERE acc=? ORDER BY id DESC",
        (session["acc"],)
    )
    history = cur.fetchall()

    conn.close()

    # 3️⃣ Dashboard ko data bhejna
    return render_template(
        "dashboard.html",
        balance=bal,
        history=history
    )

@app.route("/deposit", methods=["POST"])
def deposit():
    if "acc" not in session:
        return redirect("/")

    amount = int(request.form["amount"])

    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT balance FROM users WHERE acc=?", (session["acc"],))
    bal = cur.fetchone()[0]

    if amount <= 0:
        conn.close()
        return render_template(
            "dashboard.html",
            balance=bal,
            deposit_error="Deposit must be greater than 0",
            history=[]
        )

    # ✅ balance update
    cur.execute(
        "UPDATE users SET balance = balance + ? WHERE acc=?",
        (amount, session["acc"])
    )

    # ✅ transaction insert
    cur.execute(
        "INSERT INTO transactions (acc, type, amount) VALUES (?, ?, ?)",
        (session["acc"], "Deposit", amount)
    )

    conn.commit()
    conn.close()

    return redirect("/dashboard")
@app.route("/withdraw", methods=["POST"])
def withdraw():
    if "acc" not in session:
        return redirect("/")

    amount = int(request.form["amount"])

    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT balance FROM users WHERE acc=?", (session["acc"],))
    bal = cur.fetchone()[0]

    if amount <= 0:
        conn.close()
        return render_template(
            "dashboard.html",
            balance=bal,
            withdraw_error="Withdraw must be greater than 0",
            history=[]
        )

    if amount > bal:
        conn.close()
        return render_template(
            "dashboard.html",
            balance=bal,
            withdraw_error="Insufficient Balance",
            history=[]
        )

    cur.execute(
        "UPDATE users SET balance = balance - ? WHERE acc=?",
        (amount, session["acc"])
    )

    cur.execute(
        "INSERT INTO transactions (acc, type, amount) VALUES (?, ?, ?)",
        (session["acc"], "Withdraw", amount)
    )

    conn.commit()
    conn.close()

    return redirect("/dashboard")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


if __name__ == "__main__":
    setup_db()
    app.run(debug=True)