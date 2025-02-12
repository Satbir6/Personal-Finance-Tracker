from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session, make_response
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import os
import calendar
from dateutil.relativedelta import relativedelta

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///finance_tracker.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Database Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    currency = db.Column(db.String(10), default='₹')
    date_format = db.Column(db.String(20), default='DD/MM/YYYY')
    timezone = db.Column(db.String(50), default='Asia/Kolkata')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    transactions = db.relationship('Transaction', backref='user', lazy=True)
    categories = db.relationship('Category', backref='user', lazy=True)
    budgets = db.relationship('Budget', backref='user', lazy=True)

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(50), nullable=False)
    type = db.Column(db.String(10), nullable=False)  # 'income' or 'expense'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    transactions = db.relationship('Transaction', backref='category', lazy=True)
    budgets = db.relationship('Budget', backref='category', lazy=True)

class Transaction(db.Model):
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
        """Calculate how much has been spent in this budget's category during the current period"""
        from sqlalchemy import and_
        
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
    return User.query.get(int(user_id))

# Routes
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        
        if User.query.filter_by(email=email).first():
            flash('Email already exists')
            return redirect(url_for('register'))
        
        user = User(
            name=name,
            email=email,
            password_hash=generate_password_hash(password)
        )
        db.session.add(user)
        db.session.commit()
        
        # Create default expense categories
        expense_categories = [
            'Housing', 'Transportation', 'Food', 'Utilities', 
            'Insurance', 'Healthcare', 'Entertainment',
            'Personal Care', 'Education', 'Gifts', 'Other'
        ]
        # Create default income categories
        income_categories = [
            'Salary', 'Bonus', 'Allowance', 'Petty Cash', 
            'Investment', 'Interest', 'Rental', 'Other Income'
        ]
        
        for category_name in expense_categories:
            category = Category(name=category_name, user_id=user.id, type='expense')
            db.session.add(category)
        
        for category_name in income_categories:
            category = Category(name=category_name, user_id=user.id, type='income')
            db.session.add(category)
            
        db.session.commit()
        
        login_user(user)
        return redirect(url_for('dashboard'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('dashboard'))
        
        flash('Invalid email or password')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    # Get timeframe from query parameters (default to 'month')
    timeframe = request.args.get('timeframe', 'month')
    
    # Calculate date ranges based on timeframe
    today = datetime.utcnow()
    if timeframe == 'month':
        start_date = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        last_start_date = (start_date - timedelta(days=1)).replace(day=1)
    elif timeframe == 'quarter':
        current_quarter = (today.month - 1) // 3 + 1
        start_date = today.replace(month=(current_quarter - 1) * 3 + 1, day=1)
        end_date = today

        # Calculate last quarter's dates
        if current_quarter == 1:
            # If current quarter is Q1, last quarter was Q4 of previous year
            last_start_date = start_date.replace(year=start_date.year - 1, month=10, day=1)
            last_end_date = last_start_date.replace(month=12, day=31)
        else:
            # Otherwise, last quarter was in the same year
            last_start_date = start_date.replace(month=((current_quarter - 2) * 3 + 1))
            last_end_date = start_date - timedelta(days=1)
    else:  # year
        start_date = today.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        last_start_date = start_date.replace(year=start_date.year - 1)

    # Get current period's data
    current_transactions = Transaction.query.filter(
        Transaction.user_id == current_user.id,
        Transaction.date >= start_date,
        Transaction.date <= today
    ).all()

    # Get previous period's data
    previous_transactions = Transaction.query.filter(
        Transaction.user_id == current_user.id,
        Transaction.date >= last_start_date,
        Transaction.date < start_date
    ).all()

    # Calculate current period metrics
    current_income = sum(t.amount for t in current_transactions if t.type == 'income')
    current_expenses = sum(t.amount for t in current_transactions if t.type == 'expense')
    current_savings = current_income - current_expenses
    current_balance = current_savings

    # Calculate previous period metrics
    previous_income = sum(t.amount for t in previous_transactions if t.type == 'income')
    previous_expenses = sum(t.amount for t in previous_transactions if t.type == 'expense')
    previous_savings = previous_income - previous_expenses

    # Calculate percentage changes
    income_change = ((current_income - previous_income) / previous_income * 100) if previous_income > 0 else 0
    expenses_change = ((current_expenses - previous_expenses) / previous_expenses * 100) if previous_expenses > 0 else 0
    savings_change = ((current_savings - previous_savings) / previous_savings * 100) if previous_savings > 0 else 0
    balance_change = savings_change

    # Get recent transactions
    recent_transactions = Transaction.query.filter_by(user_id=current_user.id).order_by(Transaction.date.desc()).limit(5).all()

    # Get data for charts
    trend_labels = []
    income_trend = []
    expenses_trend = []
    
    if timeframe == 'month':
        days_in_month = calendar.monthrange(today.year, today.month)[1]
        for day in range(1, days_in_month + 1):
            date = today.replace(day=day)
            if date <= today:
                trend_labels.append(date.strftime('%d %b'))
                day_transactions = [t for t in current_transactions if t.date.day == day]
                income_trend.append(sum(t.amount for t in day_transactions if t.type == 'income'))
                expenses_trend.append(sum(t.amount for t in day_transactions if t.type == 'expense'))
    elif timeframe == 'quarter':
        for month in range(3):
            date = start_date.replace(month=start_date.month + month)
            if date <= today:
                trend_labels.append(date.strftime('%b %Y'))
                month_transactions = [t for t in current_transactions if t.date.month == date.month]
                income_trend.append(sum(t.amount for t in month_transactions if t.type == 'income'))
                expenses_trend.append(sum(t.amount for t in month_transactions if t.type == 'expense'))
    else:  # year
        for month in range(12):
            date = start_date.replace(month=month + 1)
            if date <= today:
                trend_labels.append(date.strftime('%b %Y'))
                month_transactions = [t for t in current_transactions if t.date.month == date.month]
                income_trend.append(sum(t.amount for t in month_transactions if t.type == 'income'))
                expenses_trend.append(sum(t.amount for t in month_transactions if t.type == 'expense'))

    # Get spending by category data
    category_data = {}
    for transaction in current_transactions:
        if transaction.type == 'expense':
            category_name = transaction.category.name
            if category_name not in category_data:
                category_data[category_name] = 0
            category_data[category_name] += transaction.amount

    category_labels = list(category_data.keys())
    category_amounts = list(category_data.values())

    return render_template(
        'dashboard.html',
        balance=current_balance,
        balance_change=balance_change,
        income=current_income,
        income_change=income_change,
        expenses=current_expenses,
        expenses_change=expenses_change,
        savings=current_savings,
        savings_change=savings_change,
        transactions=recent_transactions,
        trend_labels=trend_labels,
        income_trend=income_trend,
        expenses_trend=expenses_trend,
        category_labels=category_labels,
        category_amounts=category_amounts,
        categories=Category.query.filter_by(user_id=current_user.id).all()
    )

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
        datetime=datetime
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

@app.route('/budgets')
@login_required
def budgets():
    budgets = Budget.query.filter_by(user_id=current_user.id).all()
    categories = Category.query.filter_by(user_id=current_user.id).all()
    return render_template('budgets.html', budgets=budgets, categories=categories)

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
                         savings_data=savings_data)

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
                         currencies=['₹'],
                         date_formats=['DD/MM/YYYY', 'MM/DD/YYYY', 'YYYY-MM-DD'],
                         timezones=['Asia/Kolkata', 'UTC', 'US/Pacific', 'US/Eastern', 'Europe/London'])

@app.route('/dashboard/chart-data')
@login_required
def get_chart_data():
    timeframe = request.args.get('timeframe', 'This Year')
    today = datetime.utcnow()
    
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
    
    return jsonify({
        'trend_labels': labels,
        'income_trend': income_data,
        'expenses_trend': expenses_data
    })

@app.route('/dashboard/category-data')
@login_required
def get_category_data():
    timeframe = request.args.get('timeframe', 'This Month')
    today = datetime.utcnow()
    
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
    
    category_data = db.session.query(
        Category.name,
        db.func.sum(Transaction.amount)
    ).join(Transaction).filter(
        Transaction.user_id == current_user.id,
        Transaction.type == 'expense',
        Transaction.date >= start_date,
        Transaction.date < end_date
    ).group_by(Category.name).all()
    
    return jsonify({
        'category_labels': [item[0] for item in category_data],
        'category_amounts': [float(item[1]) for item in category_data]
    })

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True) 