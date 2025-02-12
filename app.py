"""
Personal Finance Tracker Web Application

A Flask-based web application for tracking personal finances, including income,
expenses, budgets, and financial reports. Features include user authentication,
transaction management, budget tracking, and data visualization.

Author: Personal Finance Tracker Team
Version: 1.0.0
License: MIT
"""

# === Standard Library Imports ===
import os
import calendar
from datetime import datetime, timedelta

# === Third-Party Imports ===
from flask import (
    Flask, 
    render_template, 
    request, 
    redirect, 
    url_for, 
    flash, 
    jsonify, 
    session, 
    make_response
)
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager, 
    UserMixin, 
    login_user, 
    login_required, 
    logout_user, 
    current_user
)
from werkzeug.security import generate_password_hash, check_password_hash
from dateutil.relativedelta import relativedelta
import pytz
from sqlalchemy import and_

# === Application Configuration ===
app = Flask(__name__)

# Security and Database Configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', os.urandom(24))
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    'DATABASE_URL', 
    'sqlite:///finance_tracker.db'
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize Extensions
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'error'

# === Database Models ===
class User(UserMixin, db.Model):
    """User model for authentication and profile management.
    
    Attributes:
        id (int): Primary key
        name (str): User's full name
        email (str): User's email address (unique)
        password_hash (str): Hashed password
        currency (str): Preferred currency symbol
        date_format (str): Preferred date format
        timezone (str): User's timezone
        created_at (datetime): Account creation timestamp
        updated_at (datetime): Last update timestamp
    """
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    currency = db.Column(db.String(10), default='$')
    date_format = db.Column(db.String(20), default='DD/MM/YYYY')
    timezone = db.Column(db.String(50), default='UTC')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    transactions = db.relationship('Transaction', backref='user', lazy=True)
    categories = db.relationship('Category', backref='user', lazy=True)
    budgets = db.relationship('Budget', backref='user', lazy=True)

class Category(db.Model):
    """Category model for organizing transactions.
    
    Attributes:
        id (int): Primary key
        user_id (int): Foreign key to User
        name (str): Category name
        type (str): Either 'income' or 'expense'
        created_at (datetime): Creation timestamp
        updated_at (datetime): Last update timestamp
    """
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(50), nullable=False)
    type = db.Column(db.String(10), nullable=False)  # 'income' or 'expense'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    transactions = db.relationship('Transaction', backref='category', lazy=True)
    budgets = db.relationship('Budget', backref='category', lazy=True)

class Transaction(db.Model):
    """Transaction model for tracking financial movements.
    
    Attributes:
        id (int): Primary key
        user_id (int): Foreign key to User
        category_id (int): Foreign key to Category
        amount (float): Transaction amount
        type (str): Either 'income' or 'expense'
        description (str): Transaction description
        date (datetime): Transaction date
        tags (str): Optional comma-separated tags
        recurring (bool): Whether transaction repeats
        created_at (datetime): Creation timestamp
        updated_at (datetime): Last update timestamp
    """
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    type = db.Column(db.String(10), nullable=False)  # 'income' or 'expense'
    description = db.Column(db.String(200))
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    tags = db.Column(db.String(200))
    recurring = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Budget(db.Model):
    """Budget model for tracking spending limits.
    
    Attributes:
        id (int): Primary key
        user_id (int): Foreign key to User
        category_id (int): Foreign key to Category
        limit_amount (float): Budget limit
        timeframe (str): Budget period (e.g., 'monthly')
        start_date (datetime): Budget start date
        end_date (datetime): Budget end date
        created_at (datetime): Creation timestamp
        updated_at (datetime): Last update timestamp
    """
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)
    limit_amount = db.Column(db.Float, nullable=False)
    timeframe = db.Column(db.String(20), nullable=False, default='monthly')
    start_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    end_date = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def get_spent(self):
        """Calculate how much has been spent in this budget's category during the current period.
        
        Returns:
            float: Total amount spent in the budget's category for the current period
        """
        # Get the start of the current period based on timeframe
        now = datetime.utcnow()
        if self.timeframe == 'monthly':
            period_start = datetime(now.year, now.month, 1)
        elif self.timeframe == 'weekly':
            period_start = now - timedelta(days=now.weekday())
        else:  # yearly
            period_start = datetime(now.year, 1, 1)
            
        # Calculate total expenses for this category in the current period
        total = db.session.query(db.func.sum(Transaction.amount)).filter(
            and_(
                Transaction.category_id == self.category_id,
                Transaction.user_id == self.user_id,
                Transaction.type == 'expense',
                Transaction.date >= period_start
            )
        ).scalar()
        
        return total or 0.0

@login_manager.user_loader
def load_user(user_id):
    """Load user by ID for Flask-Login.
    
    Args:
        user_id (int): User ID to load
        
    Returns:
        User: User object if found, None otherwise
    """
    return User.query.get(int(user_id))

# === Authentication Routes ===
@app.route('/')
def index():
    """Landing page route.
    
    Returns:
        template: Renders index.html for unauthenticated users,
                 redirects to dashboard for authenticated users
    """
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    """User registration route.
    
    Returns:
        template: Renders register.html for GET requests,
                 creates new user and redirects to dashboard for valid POST requests
    """
    if request.method == 'POST':
        try:
            # Validate email uniqueness
            if User.query.filter_by(email=request.form.get('email')).first():
                flash('Email already exists', 'error')
                return redirect(url_for('register'))
            
            # Create new user
            user = User(
                name=request.form.get('name'),
                email=request.form.get('email'),
                password_hash=generate_password_hash(request.form.get('password'))
            )
            db.session.add(user)
            db.session.commit()
            
            # Create default categories
            _create_default_categories(user.id)
            
            login_user(user)
            return redirect(url_for('dashboard'))
        except Exception as e:
            db.session.rollback()
            flash('Error during registration', 'error')
            return redirect(url_for('register'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login route.
    
    Returns:
        template: Renders login.html for GET requests,
                 authenticates and redirects to dashboard for valid POST requests
    """
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('dashboard'))
        
        flash('Invalid email or password', 'error')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    """User logout route.
    
    Returns:
        redirect: Redirects to index page after logging out
    """
    logout_user()
    return redirect(url_for('index'))

# === Dashboard Routes ===
@app.route('/dashboard')
@login_required
def dashboard():
    """Main dashboard route showing financial overview.
    
    Returns:
        template: Renders dashboard.html with financial metrics and charts
    """
    timeframe = request.args.get('timeframe', 'month')
    
    # Calculate date ranges and metrics
    metrics = _calculate_dashboard_metrics(timeframe)
    
    # Get recent transactions
    recent_transactions = Transaction.query.filter_by(user_id=current_user.id)\
        .order_by(Transaction.date.desc())\
        .limit(5).all()
    
    # Get chart data
    chart_data = _get_dashboard_chart_data(timeframe, metrics['start_date'])
    
    # Get category spending data
    category_data = _get_category_spending_data(
        metrics['current_transactions']
    )
    
    return render_template(
        'dashboard.html',
        balance=metrics['current_balance'],
        balance_change=metrics['balance_change'],
        income=metrics['current_income'],
        income_change=metrics['income_change'],
        expenses=metrics['current_expenses'],
        expenses_change=metrics['expenses_change'],
        savings=metrics['current_savings'],
        savings_change=metrics['savings_change'],
        transactions=recent_transactions,
        trend_labels=chart_data['labels'],
        income_trend=chart_data['income'],
        expenses_trend=chart_data['expenses'],
        category_labels=category_data['labels'],
        category_amounts=category_data['amounts'],
        categories=Category.query.filter_by(user_id=current_user.id).all(),
        user=current_user
    )

@app.route('/dashboard/chart-data')
@login_required
def get_chart_data():
    """AJAX endpoint for dashboard chart data.
    
    Returns:
        json: Chart data including labels and trend values
    """
    timeframe = request.args.get('timeframe', 'This Year')
    today = datetime.utcnow()
    
    # Calculate date ranges and prepare data
    chart_data = _prepare_chart_data(timeframe, today)
    
    return jsonify({
        'trend_labels': chart_data['labels'],
        'income_trend': chart_data['income'],
        'expenses_trend': chart_data['expenses']
    })

@app.route('/dashboard/category-data')
@login_required
def get_category_data():
    """AJAX endpoint for dashboard category spending data.
    
    Returns:
        json: Category spending data including labels and amounts
    """
    timeframe = request.args.get('timeframe', 'This Month')
    today = datetime.utcnow()
    
    # Calculate date ranges and category data
    category_data = _get_category_data_for_period(timeframe, today)
    
    return jsonify({
        'category_labels': category_data['labels'],
        'category_amounts': category_data['amounts']
    })

# === Transactions Routes ===
@app.route('/transactions')
@login_required
def transactions():
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    # Base query
    query = Transaction.query.filter_by(user_id=current_user.id)
    
    # Apply search filter
    search = request.args.get('search', '')
    if search:
        query = query.filter(Transaction.description.ilike(f'%{search}%'))
    
    # Apply type filter
    type_filter = request.args.get('type')
    if type_filter and type_filter != 'all':
        query = query.filter_by(type=type_filter)
    
    # Get paginated results
    transactions = query.order_by(Transaction.date.desc()).paginate(page=page, per_page=per_page)
    
    # Get categories separated by type
    income_categories = Category.query.filter_by(user_id=current_user.id, type='income').all()
    expense_categories = Category.query.filter_by(user_id=current_user.id, type='expense').all()
    
    return render_template('transactions.html',
        transactions=transactions,
        income_categories=income_categories,
        expense_categories=expense_categories,
        datetime=datetime,
        user=current_user
    )

@app.route('/transactions/add', methods=['POST'])
@login_required
def add_transaction():
    if request.method == 'POST':
        try:
            transaction = Transaction(
                user_id=current_user.id,
                category_id=request.form.get('category'),
                amount=float(request.form.get('amount')),
                type=request.form.get('type'),
                description=request.form.get('description'),
                date=datetime.strptime(request.form.get('date'), '%Y-%m-%d')
            )
            db.session.add(transaction)
            db.session.commit()
            flash('Transaction added successfully', 'success')
        except Exception as e:
            db.session.rollback()
            flash('Error adding transaction', 'error')
            
    return redirect(url_for('transactions'))

@app.route('/transactions/<int:id>/delete', methods=['POST'])
@login_required
def delete_transaction(id):
    transaction = Transaction.query.get_or_404(id)
    if transaction.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        db.session.delete(transaction)
        db.session.commit()
        return jsonify({'message': 'Transaction deleted successfully'})
    except:
        db.session.rollback()
        return jsonify({'error': 'Error deleting transaction'}), 500

@app.route('/transactions/<int:id>/edit', methods=['POST'])
@login_required
def edit_transaction(id):
    transaction = Transaction.query.get_or_404(id)
    if transaction.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        transaction.category_id = request.form.get('category')
        transaction.amount = float(request.form.get('amount'))
        transaction.type = request.form.get('type')
        transaction.description = request.form.get('description')
        transaction.date = datetime.strptime(request.form.get('date'), '%Y-%m-%d')
        db.session.commit()
        flash('Transaction updated successfully', 'success')
    except:
        db.session.rollback()
        flash('Error updating transaction', 'error')
    
    return redirect(url_for('transactions'))

# === Budgets Routes ===
@app.route('/budgets')
@login_required
def budgets():
    budgets = Budget.query.filter_by(user_id=current_user.id).all()
    categories = Category.query.filter_by(user_id=current_user.id).all()
    return render_template('budgets.html', budgets=budgets, categories=categories, user=current_user)

@app.route('/budgets/add', methods=['POST'])
@login_required
def add_budget():
    if request.method == 'POST':
        try:
            # Check if a budget already exists for this category
            existing_budget = Budget.query.filter_by(
                user_id=current_user.id,
                category_id=request.form.get('category')
            ).first()
            
            if existing_budget:
                flash('A budget already exists for this category')
                return redirect(url_for('budgets'))
            
            budget = Budget(
                user_id=current_user.id,
                category_id=request.form.get('category'),
                limit_amount=float(request.form.get('limit_amount')),
                timeframe=request.form.get('timeframe')
            )
            db.session.add(budget)
            db.session.commit()
            flash('Budget added successfully')
        except Exception as e:
            db.session.rollback()
            flash('Error adding budget')
            
    return redirect(url_for('budgets'))

@app.route('/budgets/<int:id>/delete', methods=['POST'])
@login_required
def delete_budget(id):
    budget = Budget.query.get_or_404(id)
    if budget.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        db.session.delete(budget)
        db.session.commit()
        return jsonify({'message': 'Budget deleted successfully'})
    except:
        db.session.rollback()
        return jsonify({'error': 'Error deleting budget'}), 500

@app.route('/budgets/<int:id>/edit', methods=['POST'])
@login_required
def edit_budget(id):
    budget = Budget.query.get_or_404(id)
    if budget.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        budget.category_id = request.form.get('category')
        budget.limit_amount = float(request.form.get('limit_amount'))
        budget.timeframe = request.form.get('timeframe')
        db.session.commit()
        flash('Budget updated successfully', 'success')
    except:
        db.session.rollback()
        flash('Error updating budget', 'error')
    
    return redirect(url_for('budgets'))

# === Reports Routes ===
@app.route('/reports')
@login_required
def reports():
    # Get the timeframe from query parameters (default to 'month')
    timeframe = request.args.get('timeframe', 'month')
    
    # Calculate date ranges
    now = datetime.utcnow()
    if timeframe == 'month':
        start_date = datetime(now.year, now.month, 1)
        end_date = start_date + relativedelta(months=1)
        prev_start = start_date - relativedelta(months=1)
        prev_end = start_date
    elif timeframe == 'quarter':
        quarter = (now.month - 1) // 3
        start_date = datetime(now.year, quarter * 3 + 1, 1)
        end_date = start_date + relativedelta(months=3)
        prev_start = start_date - relativedelta(months=3)
        prev_end = start_date
    else:  # year
        start_date = datetime(now.year, 1, 1)
        end_date = datetime(now.year + 1, 1, 1)
        prev_start = datetime(now.year - 1, 1, 1)
        prev_end = start_date

    # Calculate current period metrics
    current_income = db.session.query(db.func.sum(Transaction.amount)).filter(
        Transaction.user_id == current_user.id,
        Transaction.type == 'income',
        Transaction.date >= start_date,
        Transaction.date < end_date
    ).scalar() or 0

    current_expenses = db.session.query(db.func.sum(Transaction.amount)).filter(
        Transaction.user_id == current_user.id,
        Transaction.type == 'expense',
        Transaction.date >= start_date,
        Transaction.date < end_date
    ).scalar() or 0

    # Calculate previous period metrics
    prev_income = db.session.query(db.func.sum(Transaction.amount)).filter(
        Transaction.user_id == current_user.id,
        Transaction.type == 'income',
        Transaction.date >= prev_start,
        Transaction.date < prev_end
    ).scalar() or 0

    prev_expenses = db.session.query(db.func.sum(Transaction.amount)).filter(
        Transaction.user_id == current_user.id,
        Transaction.type == 'expense',
        Transaction.date >= prev_start,
        Transaction.date < prev_end
    ).scalar() or 0

    # Calculate changes
    income_change = ((current_income - prev_income) / prev_income * 100) if prev_income > 0 else 0
    expenses_change = ((current_expenses - prev_expenses) / prev_expenses * 100) if prev_expenses > 0 else 0
    
    current_savings = current_income - current_expenses
    prev_savings = prev_income - prev_expenses
    savings_change = ((current_savings - prev_savings) / prev_savings * 100) if prev_savings > 0 else 0
    
    savings_rate = (current_savings / current_income * 100) if current_income > 0 else 0
    prev_savings_rate = (prev_savings / prev_income * 100) if prev_income > 0 else 0
    savings_rate_change = savings_rate - prev_savings_rate

    # Get trend data
    if timeframe == 'month':
        trend_dates = [start_date + timedelta(days=x) for x in range(0, 31)]
    elif timeframe == 'quarter':
        trend_dates = [start_date + relativedelta(months=x) for x in range(0, 3)]
    else:
        trend_dates = [start_date + relativedelta(months=x) for x in range(0, 12)]

    trend_labels = [d.strftime('%Y-%m-%d') for d in trend_dates]
    
    # Get income and expenses for each date in the trend
    income_trend = []
    expenses_trend = []
    for date in trend_dates:
        if timeframe == 'month':
            period_start = date
            period_end = date + timedelta(days=1)
        else:
            period_start = date
            period_end = date + relativedelta(months=1)
            
        income = db.session.query(db.func.sum(Transaction.amount)).filter(
            Transaction.user_id == current_user.id,
            Transaction.type == 'income',
            Transaction.date >= period_start,
            Transaction.date < period_end
        ).scalar() or 0
        
        expenses = db.session.query(db.func.sum(Transaction.amount)).filter(
            Transaction.user_id == current_user.id,
            Transaction.type == 'expense',
            Transaction.date >= period_start,
            Transaction.date < period_end
        ).scalar() or 0
        
        income_trend.append(income)
        expenses_trend.append(expenses)

    # Get category data
    category_data = db.session.query(
        Category.name,
        db.func.sum(Transaction.amount)
    ).join(Transaction).filter(
        Transaction.user_id == current_user.id,
        Transaction.type == 'expense',
        Transaction.date >= start_date,
        Transaction.date < end_date
    ).group_by(Category.name).all()

    category_labels = [item[0] for item in category_data]
    category_amounts = [float(item[1]) for item in category_data]

    # Get budget vs actual data
    budgets = Budget.query.filter_by(user_id=current_user.id).all()
    budget_labels = []
    budget_data = []
    actual_data = []

    for budget in budgets:
        budget_labels.append(budget.category.name)
        budget_data.append(float(budget.limit_amount))
        actual_data.append(float(budget.get_spent()))

    # Calculate monthly savings data
    savings_labels = []
    savings_data = []
    for i in range(6):
        month_start = now - relativedelta(months=i)
        month_start = datetime(month_start.year, month_start.month, 1)
        month_end = month_start + relativedelta(months=1)
        
        month_income = db.session.query(db.func.sum(Transaction.amount)).filter(
            Transaction.user_id == current_user.id,
            Transaction.type == 'income',
            Transaction.date >= month_start,
            Transaction.date < month_end
        ).scalar() or 0
        
        month_expenses = db.session.query(db.func.sum(Transaction.amount)).filter(
            Transaction.user_id == current_user.id,
            Transaction.type == 'expense',
            Transaction.date >= month_start,
            Transaction.date < month_end
        ).scalar() or 0
        
        savings_labels.insert(0, month_start.strftime('%b %Y'))
        savings_data.insert(0, month_income - month_expenses)

    return render_template('reports.html',
                         total_income=current_income,
                         total_expenses=current_expenses,
                         net_savings=current_savings,
                         savings_rate=savings_rate,
                         income_change=income_change,
                         expenses_change=expenses_change,
                         savings_change=savings_change,
                         savings_rate_change=savings_rate_change,
                         trend_labels=trend_labels,
                         income_trend=income_trend,
                         expenses_trend=expenses_trend,
                         category_labels=category_labels,
                         category_data=category_amounts,
                         budget_labels=budget_labels,
                         budget_data=budget_data,
                         actual_data=actual_data,
                         savings_labels=savings_labels,
                         savings_data=savings_data,
                         user=current_user)

@app.route('/reports/export')
@login_required
def export_reports():
    # Get the timeframe from query parameters (default to 'month')
    timeframe = request.args.get('timeframe', 'month')
    
    # Calculate date ranges
    now = datetime.utcnow()
    if timeframe == 'month':
        start_date = datetime(now.year, now.month, 1)
        end_date = start_date + relativedelta(months=1)
    elif timeframe == 'quarter':
        quarter = (now.month - 1) // 3
        start_date = datetime(now.year, quarter * 3 + 1, 1)
        end_date = start_date + relativedelta(months=3)
    else:  # year
        start_date = datetime(now.year, 1, 1)
        end_date = datetime(now.year + 1, 1, 1)

    # Get transactions for the period
    transactions = Transaction.query.filter(
        Transaction.user_id == current_user.id,
        Transaction.date >= start_date,
        Transaction.date < end_date
    ).order_by(Transaction.date).all()

    # Create CSV content
    csv_content = "Date,Type,Category,Description,Amount\n"
    for t in transactions:
        csv_content += f"{t.date.strftime('%Y-%m-%d')},{t.type},{t.category.name},{t.description},{t.amount}\n"

    # Create response
    response = make_response(csv_content)
    response.headers['Content-Type'] = 'text/csv'
    response.headers['Content-Disposition'] = f'attachment; filename=finance_report_{timeframe}_{now.strftime("%Y%m%d")}.csv'
    
    return response

# === Settings Routes ===
@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    if request.method == 'POST':
        try:
            current_user.name = request.form.get('name')
            current_user.email = request.form.get('email')
            current_user.currency = request.form.get('currency')
            current_user.date_format = request.form.get('date_format')
            current_user.timezone = request.form.get('timezone')
            
            # Handle password change
            current_password = request.form.get('current_password')
            new_password = request.form.get('new_password')
            if current_password and new_password:
                if check_password_hash(current_user.password_hash, current_password):
                    current_user.password_hash = generate_password_hash(new_password)
                else:
                    flash('Current password is incorrect', 'error')
                    return redirect(url_for('settings'))
            
            db.session.commit()
            flash('Settings updated successfully', 'success')
        except:
            db.session.rollback()
            flash('Error updating settings', 'error')
        
        return redirect(url_for('settings'))
    
    return render_template('settings.html',
                         currencies=['$', '€', '£', '¥', '₹'],
                         date_formats=['DD/MM/YYYY', 'MM/DD/YYYY', 'YYYY-MM-DD'],
                         timezones=['Asia/Kolkata', 'UTC', 'US/Pacific', 'US/Eastern', 'Europe/London'])

# === Helper Functions ===
def _create_default_categories(user_id):
    """Create default income and expense categories for new users.
    
    Args:
        user_id (int): ID of the user to create categories for
    """
    expense_categories = [
        'Housing', 'Transportation', 'Food', 'Utilities', 
        'Insurance', 'Healthcare', 'Entertainment',
        'Personal Care', 'Education', 'Gifts', 'Other'
    ]
    income_categories = [
        'Salary', 'Bonus', 'Allowance', 'Petty Cash', 
        'Investment', 'Interest', 'Rental', 'Other Income'
    ]
    
    for category_name in expense_categories:
        category = Category(name=category_name, user_id=user_id, type='expense')
        db.session.add(category)
    
    for category_name in income_categories:
        category = Category(name=category_name, user_id=user_id, type='income')
        db.session.add(category)
        
    db.session.commit()

def _calculate_dashboard_metrics(timeframe):
    """Calculate financial metrics for the dashboard.
    
    Args:
        timeframe (str): Period to calculate metrics for ('month', 'quarter', 'year')
        
    Returns:
        dict: Dictionary containing calculated metrics
    """
    today = datetime.utcnow()
    
    # Calculate date ranges
    if timeframe == 'month':
        start_date = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        last_start_date = (start_date - timedelta(days=1)).replace(day=1)
    elif timeframe == 'quarter':
        current_quarter = (today.month - 1) // 3 + 1
        start_date = today.replace(month=(current_quarter - 1) * 3 + 1, day=1)
        if current_quarter == 1:
            last_start_date = start_date.replace(year=start_date.year - 1, month=10, day=1)
        else:
            last_start_date = start_date.replace(month=((current_quarter - 2) * 3 + 1))
    else:  # year
        start_date = today.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        last_start_date = start_date.replace(year=start_date.year - 1)
    
    # Get transactions for current and previous periods
    current_transactions = Transaction.query.filter(
        Transaction.user_id == current_user.id,
        Transaction.date >= start_date,
        Transaction.date <= today
    ).all()
    
    previous_transactions = Transaction.query.filter(
        Transaction.user_id == current_user.id,
        Transaction.date >= last_start_date,
        Transaction.date < start_date
    ).all()
    
    # Calculate metrics
    current_income = sum(t.amount for t in current_transactions if t.type == 'income')
    current_expenses = sum(t.amount for t in current_transactions if t.type == 'expense')
    current_savings = current_income - current_expenses
    current_balance = current_savings
    
    previous_income = sum(t.amount for t in previous_transactions if t.type == 'income')
    previous_expenses = sum(t.amount for t in previous_transactions if t.type == 'expense')
    previous_savings = previous_income - previous_expenses
    
    # Calculate changes
    income_change = ((current_income - previous_income) / previous_income * 100) if previous_income > 0 else 0
    expenses_change = ((current_expenses - previous_expenses) / previous_expenses * 100) if previous_expenses > 0 else 0
    savings_change = ((current_savings - previous_savings) / previous_savings * 100) if previous_savings > 0 else 0
    balance_change = savings_change
    
    return {
        'start_date': start_date,
        'current_transactions': current_transactions,
        'current_income': current_income,
        'current_expenses': current_expenses,
        'current_savings': current_savings,
        'current_balance': current_balance,
        'income_change': income_change,
        'expenses_change': expenses_change,
        'savings_change': savings_change,
        'balance_change': balance_change
    }

def _get_dashboard_chart_data(timeframe, start_date):
    """Get chart data for the dashboard.
    
    Args:
        timeframe (str): Period to get data for ('month', 'quarter', 'year')
        start_date (datetime): Start date of the period
        
    Returns:
        dict: Dictionary containing chart labels and data series
    """
    today = datetime.utcnow()
    trend_labels = []
    income_trend = []
    expenses_trend = []
    
    if timeframe == 'month':
        days_in_month = calendar.monthrange(today.year, today.month)[1]
        for day in range(1, days_in_month + 1):
            date = today.replace(day=day)
            if date <= today:
                trend_labels.append(date.strftime('%d %b'))
                
                # Get transactions for this day
                day_transactions = Transaction.query.filter(
                    Transaction.user_id == current_user.id,
                    Transaction.date >= date,
                    Transaction.date < date + timedelta(days=1)
                ).all()
                
                income_trend.append(sum(t.amount for t in day_transactions if t.type == 'income'))
                expenses_trend.append(sum(t.amount for t in day_transactions if t.type == 'expense'))
    
    elif timeframe == 'quarter':
        for month in range(3):
            date = start_date.replace(month=start_date.month + month)
            if date <= today:
                trend_labels.append(date.strftime('%b %Y'))
                
                # Get transactions for this month
                month_transactions = Transaction.query.filter(
                    Transaction.user_id == current_user.id,
                    Transaction.date >= date,
                    Transaction.date < date + relativedelta(months=1)
                ).all()
                
                income_trend.append(sum(t.amount for t in month_transactions if t.type == 'income'))
                expenses_trend.append(sum(t.amount for t in month_transactions if t.type == 'expense'))
    
    else:  # year
        for month in range(12):
            date = start_date.replace(month=month + 1)
            if date <= today:
                trend_labels.append(date.strftime('%b %Y'))
                
                # Get transactions for this month
                month_transactions = Transaction.query.filter(
                    Transaction.user_id == current_user.id,
                    Transaction.date >= date,
                    Transaction.date < date + relativedelta(months=1)
                ).all()
                
                income_trend.append(sum(t.amount for t in month_transactions if t.type == 'income'))
                expenses_trend.append(sum(t.amount for t in month_transactions if t.type == 'expense'))
    
    return {
        'labels': trend_labels,
        'income': income_trend,
        'expenses': expenses_trend
    }

def _get_category_spending_data(transactions):
    """Calculate spending by category from a list of transactions.
    
    Args:
        transactions (list): List of Transaction objects
        
    Returns:
        dict: Dictionary containing category labels and amounts
    """
    category_data = {}
    
    for transaction in transactions:
        if transaction.type == 'expense':
            category_name = transaction.category.name
            if category_name not in category_data:
                category_data[category_name] = 0
            category_data[category_name] += transaction.amount
    
    return {
        'labels': list(category_data.keys()),
        'amounts': list(category_data.values())
    }

def _prepare_chart_data(timeframe, today):
    """Prepare chart data for AJAX endpoint.
    
    Args:
        timeframe (str): Period to prepare data for
        today (datetime): Current date
        
    Returns:
        dict: Dictionary containing chart data
    """
    if timeframe == 'This Month':
        start_date = datetime(today.year, today.month, 1)
        labels = [(start_date + timedelta(days=x)).strftime('%d %b') for x in range(31)]
        period = 'days'
    elif timeframe == 'This Quarter':
        quarter = (today.month - 1) // 3
        start_date = datetime(today.year, quarter * 3 + 1, 1)
        labels = [(start_date + relativedelta(months=x)).strftime('%b %Y') for x in range(3)]
        period = 'months'
    else:  # This Year
        start_date = datetime(today.year, 1, 1)
        labels = [(start_date + relativedelta(months=x)).strftime('%b %Y') for x in range(12)]
        period = 'months'
    
    income_data = []
    expenses_data = []
    
    for i in range(len(labels)):
        if period == 'days':
            period_start = start_date + timedelta(days=i)
            period_end = period_start + timedelta(days=1)
        else:
            period_start = start_date + relativedelta(months=i)
            period_end = period_start + relativedelta(months=1)
        
        # Get transactions for this period
        income = db.session.query(db.func.sum(Transaction.amount)).filter(
            Transaction.user_id == current_user.id,
            Transaction.type == 'income',
            Transaction.date >= period_start,
            Transaction.date < period_end
        ).scalar() or 0
        
        expenses = db.session.query(db.func.sum(Transaction.amount)).filter(
            Transaction.user_id == current_user.id,
            Transaction.type == 'expense',
            Transaction.date >= period_start,
            Transaction.date < period_end
        ).scalar() or 0
        
        income_data.append(float(income))
        expenses_data.append(float(expenses))
    
    return {
        'labels': labels,
        'income': income_data,
        'expenses': expenses_data
    }

def _get_category_data_for_period(timeframe, today):
    """Get category spending data for a specific period.
    
    Args:
        timeframe (str): Period to get data for
        today (datetime): Current date
        
    Returns:
        dict: Dictionary containing category data
    """
    if timeframe == 'This Month':
        start_date = datetime(today.year, today.month, 1)
        end_date = start_date + relativedelta(months=1)
    elif timeframe == 'This Quarter':
        quarter = (today.month - 1) // 3
        start_date = datetime(today.year, quarter * 3 + 1, 1)
        end_date = start_date + relativedelta(months=3)
    else:  # This Year
        start_date = datetime(today.year, 1, 1)
        end_date = datetime(today.year + 1, 1, 1)
    
    # Get category spending data
    category_data = db.session.query(
        Category.name,
        db.func.sum(Transaction.amount)
    ).join(Transaction).filter(
        Transaction.user_id == current_user.id,
        Transaction.type == 'expense',
        Transaction.date >= start_date,
        Transaction.date < end_date
    ).group_by(Category.name).all()
    
    return {
        'labels': [item[0] for item in category_data],
        'amounts': [float(item[1]) for item in category_data]
    }

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True) 