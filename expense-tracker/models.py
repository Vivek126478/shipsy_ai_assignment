import enum
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.ext.hybrid import hybrid_property
import datetime

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    expenses = db.relationship('Expense', backref='owner', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class ExpenseCategory(enum.Enum):
    FOOD = "Food"
    TRANSPORT = "Transport"
    UTILITIES = "Utilities"
    ENTERTAINMENT = "Entertainment"
    OTHER = "Other"

class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(200), nullable=False)
    category = db.Column(db.Enum(ExpenseCategory), nullable=False, default=ExpenseCategory.OTHER)
    is_reimbursable = db.Column(db.Boolean, default=False, nullable=False)
    base_amount = db.Column(db.Float, nullable=False)
    tax_amount = db.Column(db.Float, nullable=False, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    @hybrid_property
    def total_amount(self):
        return self.base_amount + self.tax_amount
    
    def to_dict(self):
        return {
            'id': self.id,
            'description': self.description,
            'category': self.category.value,
            'is_reimbursable': self.is_reimbursable,
            'base_amount': self.base_amount,
            'tax_amount': self.tax_amount,
            'total_amount': self.total_amount,
            'created_at': self.created_at.isoformat()
        }