from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
import datetime
from flask_bcrypt import Bcrypt

# ------------------------------------------------------------------------------
# 1. CONFIG
# ------------------------------------------------------------------------------
app = Flask(__name__)
bcrypt = Bcrypt(app)
app.config['SECRET_KEY'] = '123'  # Replace with a more secure key
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///finance.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ------------------------------------------------------------------------------
# 2. DATABASE MODELS
# ------------------------------------------------------------------------------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)

    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash.encode('utf-8'), password.encode('utf-8'))


class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.Date, default=datetime.date.today)
    description = db.Column(db.String(200), nullable=True)
    amount = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(50), nullable=True)  # e.g. "income", "expense"
    
    user = db.relationship('User', backref=db.backref('transactions', lazy=True))

# ------------------------------------------------------------------------------
# 3. UTILITY FUNCTIONS
# ------------------------------------------------------------------------------
def current_user():
    """
    Returns the current logged-in user object
    based on session['user_id'].
    """
    if 'user_id' in session:
        return db.session.get(User, session['user_id'])
    return None


def login_required(func):
    """
    Simple decorator to ensure a user is logged in.
    """
    def wrapper(*args, **kwargs):
        if not current_user():
            flash("Please log in to access this page.", "warning")
            return redirect(url_for('login'))
        return func(*args, **kwargs)
    wrapper.__name__ = func.__name__  # to avoid issues with Flask's route
    return wrapper

# ------------------------------------------------------------------------------
# 4. ROUTES
# ------------------------------------------------------------------------------

@app.route('/')
def home():
    return render_template('layout.html')  # A simple homepage or landing

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        # Check if user exists
        if User.query.filter_by(email=email).first():
            flash("Email already registered. Please log in.", "danger")
            return redirect(url_for('login'))
        
        new_user = User(email=email)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        
        flash("Registration successful! You can now log in.", "success")
        return redirect(url_for('login'))
    
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password):
            session['user_id'] = user.id
            flash("Logged in successfully!", "success")
            return redirect(url_for('dashboard'))
        else:
            flash("Invalid credentials.", "danger")
            return redirect(url_for('login'))
    
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash("Logged out.", "info")
    return redirect(url_for('login'))


@app.route('/dashboard')
@login_required
def dashboard():
    user = current_user()
    
    # Fetch all transactions for the logged-in user
    transactions = Transaction.query.filter_by(user_id=user.id).all()
    
    # Simple analytics
    total_income = sum(t.amount for t in transactions if t.category == 'income')
    total_expense = sum(t.amount for t in transactions if t.category == 'expense')
    net = total_income - total_expense
    
    # Example: naive predictive analytics
    # If the user has X average monthly expense, let's guess at next month's
    # We'll keep it ultra-simple: average monthly = total_expenses / # months (hard-coded to 1 if no data)
    # Real logic would group by months/dates.
    months_count = 1
    if len(transactions) > 0:
        first_date = min(t.date for t in transactions)
        now = datetime.date.today()
        months_count = max((now.year - first_date.year)*12 + (now.month - first_date.month), 1)
    avg_monthly_expense = total_expense / months_count
    
    predicted_next_month_expense = round(avg_monthly_expense, 2)
    
    # Event-driven notifications example
    # If net < 0, you might want to notify user
    if net < 0:
        # For demonstration, just flash a message
        flash("Warning: You have a negative net balance this period!", "warning")
    
    return render_template('dashboard.html',
                           transactions=transactions,
                           total_income=total_income,
                           total_expense=total_expense,
                           net=net,
                           predicted_next_month_expense=predicted_next_month_expense)


@app.route('/add_transaction', methods=['POST'])
@login_required
def add_transaction():
    user = current_user()
    amount = float(request.form.get('amount', 0))
    category = request.form.get('category')  # "income" or "expense"
    description = request.form.get('description')
    
    new_txn = Transaction(
        user_id=user.id,
        date=datetime.date.today(),
        description=description,
        amount=amount,
        category=category
    )
    db.session.add(new_txn)
    db.session.commit()
    
    flash("Transaction added successfully!", "success")
    return redirect(url_for('dashboard'))

# ------------------------------------------------------------------------------
# 5. DB INIT
# ------------------------------------------------------------------------------
def create_tables():
    """
    Create the database tables if they don't exist yet.
    """
    with app.app_context():
        db.create_all()

# ------------------------------------------------------------------------------
# 6. RUN (for development)
# ------------------------------------------------------------------------------
if __name__ == '__main__':
    # In production, use a WSGI server (gunicorn, etc.) and not debug mode.
    create_tables()
    app.run(debug=True)
