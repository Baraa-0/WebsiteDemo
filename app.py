import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    # Get stocks data from db shares
    stocks = db.execute(
        "SELECT symbol, price, SUM(price * shares) AS total, SUM(shares) AS shares FROM shares WHERE user_id=? GROUP BY symbol",
        session["user_id"]
    )
    print(stocks)
    cash = db.execute(
        "SELECT cash FROM users WHERE id = ?",
        session["user_id"]
    )
    total = db.execute(
        "SELECT SUM(price*shares) AS total FROM shares WHERE user_id = ?",
        session["user_id"]
    )

    return render_template("index.html", stocks=stocks, cash=cash[0]["cash"], total=total[0]["total"])


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        try:
            int(request.form.get("shares"))
        except:
            return apology("shares must bean integer", 400)

        # Ensure symbol was submitted
        if not request.form.get("symbol"):
            return apology("missing symbol", 400)

        # Ensure shares was submitted
        elif not request.form.get("shares"):
            return apology("missing shares", 400)

        # Ensure shares was positive integer
        elif int(request.form.get("shares")) < 1:
            return apology("invalid number", 400)

        # Get stock current price
        dict = lookup(request.form.get("symbol"))
        # Get user cash
        rows = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])
        if len(rows) != 1:
            return apology("database error", 403)
        # Ensure symbol is valid
        if not dict:
            return apology("invalid symbol", 400)
        # Ensure user have enough money
        elif dict["price"] * int(request.form.get("shares")) > rows[0]["cash"]:
            return apology("can't afford", 400)
        else:
            # User remaining cash
            rows[0]["cash"] = rows[0]["cash"] - dict["price"] * float(request.form.get("shares"))
            db.execute(
                "UPDATE users SET cash = ? WHERE id = ?",
                rows[0]["cash"],
                session["user_id"]
            )

            # Insert values into db shares
            db.execute(
                "INSERT INTO shares (symbol, shares, price, date, user_id) VALUES(?, ?, ?, ?, ?)",
                dict["symbol"],
                int(request.form.get("shares")),
                dict["price"],
                datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
                session["user_id"]
            )

        # Redirect user to home page
        flash("Bought!")
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("buy.html")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""

    # Get data from shares db
    rows = db.execute(
        "SELECT * FROM shares WHERE user_id=?",
        session["user_id"]
    )
    return render_template("history.html", rows=rows)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute(
            "SELECT * FROM users WHERE username = ?", request.form.get("username")
        )

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(
            rows[0]["hash"], request.form.get("password")
        ):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        flash("Logged in!")
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    flash("Logged out!")
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # Ensure that symbol was submitted
        if not request.form.get("symbol"):
            return apology("must provide symbol", 400)

        # Get stock quote from symbol
        dict = lookup(request.form.get("symbol"))
        if not dict:
            return apology("invalid symbol", 400)

        # Render quoted template
        return render_template("quoted.html", name=dict['name'], price=usd(dict['price']), symbol=dict['symbol'])

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 400)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 400)

        # Ensure password was confirmed
        elif not request.form.get("confirmation"):
            return apology("must confirm password", 400)

        # Ensure that passwords match
        elif request.form.get("password") != request.form.get("confirmation"):
            return apology("passwords does not match", 400)

        # Try to insert username and password
        try:
            id = db.execute(
                "INSERT INTO users (username, hash) VALUES(?, ?)", request.form.get("username"),
                generate_password_hash(request.form.get("password"))
            )
        except ValueError:
            return apology("username already exist", 400)

        # Remember which user has registered
        session["user_id"] = id

        # Redirect user to home page
        flash("Registered!")
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""

    # Get symbol from db
    symbols = db.execute(
        "SELECT DISTINCT symbol FROM shares WHERE user_id = ? GROUP BY symbol HAVING SUM(shares) != 0",
        session["user_id"]
    )

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Create a list of available symbols
        s = []
        for i in range(len(symbols)):
            s.append(symbols[i]["symbol"])

        # Get stock current price
        dict = lookup(request.form.get("symbol"))

        # Get number of shares in db for specific symbol
        shares = db.execute(
            "SELECT SUM(shares) AS shares FROM shares WHERE user_id=? AND symbol = ?",
            session["user_id"],
            request.form.get("symbol")
        )

        # Get user cash
        cash = db.execute(
            "SELECT cash FROM users WHERE id = ?",
            session["user_id"]
        )

        # Ensure symbol is valid
        if request.form.get("symbol") not in s:
            return apology("stock does not exist", 403)

        # Ensure shares is valid
        if not request.form.get("shares") or int(request.form.get("shares")) < 1:
            return apology("missing shares", 400)

        # Ensure user have enough shares
        if int(request.form.get("shares")) > shares[0]["shares"]:
            return apology("insuffisant shares", 400)

        # Insert values into db shares
        db.execute(
            "INSERT INTO shares (symbol, shares, price, date, user_id) VALUES(?, ?, ?, ?, ?)",
            request.form.get("symbol"),
            -int(request.form.get("shares")),
            dict["price"],
            datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
            session["user_id"]
        )

        # Add stock price to cash
        db.execute(
            "UPDATE users SET cash = ? WHERE id = ?",
            cash[0]["cash"] + dict["price"] * int(request.form.get("shares")),
            session["user_id"]
        )

        # Redirect user to home page
        flash("Sold!")
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("sell.html", symbols=symbols)


@app.route("/cash", methods=["POST"])
@login_required
def cash():

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Get user cash
        cash = db.execute(
            "SELECT cash FROM users WHERE id = ?",
            session["user_id"]
        )

        # Ensure cash is positive
        if float(request.form.get("cash")) < 1.00:
            return apology("invalid number", 403)

        # Adds cash to db
        db.execute(
            "UPDATE users SET cash = ? WHERE id = ?",
            cash[0]["cash"] + float(request.form.get("cash")),
            session["user_id"]
        )

        # Redirect user to home page
        flash("Cash added!")
        return redirect("/")
