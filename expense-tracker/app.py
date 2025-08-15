import os
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from functools import wraps
from config import Config
from models import db, User, Expense, ExpenseCategory

# --- App Factory ---
def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    db.init_app(app)

    # --- Login Required Decorator ---
    def login_required(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash('Please log in to access this page.', 'warning')
                return redirect(url_for('login'))
            return f(*args, **kwargs)
        return decorated_function

    # --- Page Routes ---
    @app.route('/')
    @login_required
    def index():
        user = db.session.get(User, session['user_id'])
        categories = [category.value for category in ExpenseCategory]
        return render_template('index.html', user=user, categories=categories)

    @app.route('/register', methods=['GET', 'POST'])
    def register():
        if request.method == 'POST':
            username = request.form['username']
            password = request.form['password']
            
            existing_user = User.query.filter_by(username=username).first()
            if existing_user:
                flash('Username already exists. Please choose a different one.', 'danger')
                return redirect(url_for('register'))

            new_user = User(username=username)
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.commit()

            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))
        return render_template('register.html')

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            username = request.form['username']
            password = request.form['password']
            user = User.query.filter_by(username=username).first()

            if user and user.check_password(password):
                session['user_id'] = user.id
                flash('Logged in successfully!', 'success')
                return redirect(url_for('index'))
            else:
                flash('Invalid username or password.', 'danger')
                return redirect(url_for('login'))
        return render_template('login.html')

    @app.route('/logout')
    def logout():
        session.pop('user_id', None)
        flash('You have been logged out.', 'info')
        return redirect(url_for('login'))

    # --- API Routes ---
    @app.route('/api/expenses', methods=['POST'])
    @login_required
    def create_expense():
        data = request.get_json()
        if not data or not data.get('description') or data.get('base_amount') is None:
            return jsonify({'error': 'Missing required fields'}), 400

        try:
            category_enum = ExpenseCategory[data.get('category', 'OTHER').upper()]
            new_expense = Expense(
                description=data['description'],
                category=category_enum,
                base_amount=float(data['base_amount']),
                tax_amount=float(data.get('tax_amount', 0.0)),
                is_reimbursable=bool(data.get('is_reimbursable', False)),
                user_id=session['user_id']
            )
            db.session.add(new_expense)
            db.session.commit()
            return jsonify(new_expense.to_dict()), 201
        except (ValueError, KeyError) as e:
            return jsonify({'error': f'Invalid data: {e}'}), 400

    @app.route('/api/expenses', methods=['GET'])
    @login_required
    def get_expenses():
        page = request.args.get('page', 1, type=int)
        category_filter = request.args.get('category', 'ALL', type=str)

        query = Expense.query.filter_by(user_id=session['user_id'])

        if category_filter != 'ALL':
            try:
                category_enum = ExpenseCategory[category_filter.upper()]
                query = query.filter_by(category=category_enum)
            except KeyError:
                return jsonify({'error': 'Invalid category specified'}), 400
        
        query = query.order_by(Expense.created_at.desc())

        pagination = query.paginate(page=page, per_page=5, error_out=False)
        expenses = pagination.items

        return jsonify({
            'expenses': [expense.to_dict() for expense in expenses],
            'total_pages': pagination.pages,
            'current_page': pagination.page,
            'has_next': pagination.has_next,
            'has_prev': pagination.has_prev
        }), 200

    @app.route('/api/expenses/<int:expense_id>', methods=['PUT'])
    @login_required
    def update_expense(expense_id):
        expense = db.session.get(Expense, expense_id)
        if not expense:
            return jsonify({'error': 'Expense not found'}), 404
        
        if expense.user_id != session['user_id']:
            return jsonify({'error': 'Unauthorized'}), 403

        data = request.get_json()
        try:
            expense.description = data.get('description', expense.description)
            if 'category' in data:
                expense.category = ExpenseCategory[data['category'].upper()]
            expense.base_amount = float(data.get('base_amount', expense.base_amount))
            expense.tax_amount = float(data.get('tax_amount', expense.tax_amount))
            expense.is_reimbursable = bool(data.get('is_reimbursable', expense.is_reimbursable))
            
            db.session.commit()
            return jsonify(expense.to_dict()), 200
        except (ValueError, KeyError) as e:
            return jsonify({'error': f'Invalid data: {e}'}), 400

    @app.route('/api/expenses/<int:expense_id>', methods=['DELETE'])
    @login_required
    def delete_expense(expense_id):
        expense = db.session.get(Expense, expense_id)
        if not expense:
            return jsonify({'error': 'Expense not found'}), 404

        if expense.user_id != session['user_id']:
            return jsonify({'error': 'Unauthorized'}), 403
            
        db.session.delete(expense)
        db.session.commit()
        return jsonify({'message': 'Expense deleted successfully'}), 200

    # --- Database Initialization ---
    with app.app_context():
        db.create_all()

    return app

app = create_app()

# Only run in local development
if __name__ == '__main__':
    app.run(debug=True)
