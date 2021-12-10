
import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd
from datetime import datetime, timezone, timedelta
#API Key
#pk_4c180b4d88b04da4bd83a93312e26241
#export API_KEY=pk_4c180b4d88b04da4bd83a93312e26241

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True


# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
os.environ["API_KEY"] = 'pk_4c180b4d88b04da4bd83a93312e26241'
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    user_cash = usd(db.execute('SELECT cash FROM users WHERE id = ?', session['user_id'])[0]['cash'])

    #brandon = db.execute('SELECT symbol, shares FROM trades WHERE username = ?', session['user_id'])

    return render_template("landing.html", user_cash = user_cash )#brandon = brandon)

@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    if request.method == "POST":
        q = lookup(request.form.get('symbol'))
        shares = request.form.get('shares')
        #make sure that symbol exists
        if not q:
            return render_template('buy.html' ,invalid_buy = True)
        else:
        #make sure that number of shares exists, and error message for non-integers is o.k.
            if shares:
                cost_basis = q["price"]
                buy_order = float(shares) * float(cost_basis)
                user_cash = db.execute('SELECT cash FROM users WHERE id = ?', session['user_id'])[0]['cash']

                if (buy_order > user_cash):
                    return apology('Woah there Nellie add more cash to make that purchase',69)

                elif (buy_order < 0):
                    return apology("Cannot buy a negative amount of shares",70)
                else:
                    remainder = user_cash - buy_order
                    #this line updates our cash in user table
                    db.execute('UPDATE users SET cash = ? WHERE id = ?', remainder, session['user_id'])

                    #All 4 below are the necessary things we need inserted into our table, need to define them to make things cleaner
                    username = db.execute('SELECT username FROM users WHERE id =?', session['user_id'])[0]['username']
                    current_time = datetime.now(timezone(timedelta(hours=-5)))
                    #needed this voodoo line to get the time to show in database
                    current_time = str(current_time.date()) + ' time: ' + current_time.time().strftime("%H:%M:%S")
                    symbol = request.form.get("symbol")
                    shares = request.form.get("shares")
                    #this line populates our trade table
                    db.execute("INSERT INTO trades (username, price, time, symbol, shares) VALUES (?,?,?,?,?)", username, cost_basis, current_time, symbol,shares)

                    return render_template('landing.html', bought = True)

            else:
                return render_template('buy.html' , no_stock = True)
        #return render_template('buy_confirmation.html', name = q["name"], price = q["price"], symbol = q["symbol"])

    else:
        return render_template('buy.html')


@app.route("/history")
@login_required
def history():

    #db.execute("INSERT INTO trades (username, price, time, symbol, shares) VALUES (?,?,?,?,?)", username, cost_basis, current_time, symbol,shares)
    """Show history of transactions"""
    #username = db.execute('SELECT username FROM users WHERE id =?', session['user_id'])[0]['username']
    username = db.execute('SELECT * FROM trades WHERE id=?',session['user_id'])['username']
    # shares = db.execute("SELECT shares FROM trades WHERE username=?",session['user_id'])['username']
    # price = db.execute("SELECT  price FROM trades WHERE username=?",session['user_id'])['username']
    # time = db.execute("SELECT time FROM trades WHERE username=?",session['user_id'])['username']
    return render_template('history.html' , username = username)

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
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
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
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method == "POST":
        #logic for case of failed lookup
        q = lookup(request.form.get('symbol'))
        if not q:
            return render_template('quote.html' ,invalid = True)
        return render_template('quoted.html', name = q["name"], price = q["price"], symbol = q["symbol"])
    #GET method, or default render
    else:
        return render_template("quote.html")

@app.route("/register", methods=["GET", "POST"])
def register():

    session.clear()

    if request.method == "POST":

        #first three branches check making sure fields filled
        if not request.form.get("username"):
            return apology("Must provide username", 403)
        elif len(db.execute('SELECT username FROM users WHERE username = ?', request.form.get('username'))) > 0:
            return apology('Username already exists, please choose another', 403)

        elif not request.form.get("password"):
            return apology("Must provide password", 403)

        elif not request.form.get("password_confirm"):
            return apology("Must provide password and confirm", 403)

        #this branch checks for matching passwords & makes sure not already in database
        elif request.form.get("username") and request.form.get("password") and request.form.get("password_confirm"):
            p_hash = generate_password_hash(request.form.get("password"))

        #compare password hash to password confirm phash, pword
            if check_password_hash(p_hash, request.form.get("password_confirm")):

                #note this line can be split up with a \ as shown
                db.execute('INSERT INTO users (username, hash) \
                VALUES(?, ?)', request.form.get("username"), p_hash)

                #Lines to remember user has now logged in and needs redirected now
                # Query database for username
                rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))


                # Remember which user has logged in
                session["user_id"] = rows[0]["id"]

                # Redirect user to home page
                return redirect("/")
            else:
                return apology("Password and Confirmation must match", 403)
    #check_password_hash(rows[0]["hash"], request.form.get("password")

    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    return apology("TODO")


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
