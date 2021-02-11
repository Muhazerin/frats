from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin
from flask_bcrypt import Bcrypt

import os


app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(12).hex()
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'index'
login_manager.login_message_category = 'warning'


@login_manager.user_loader
def load_user(user_id):
    return Users.query.get(int(user_id))


class Users(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    type = db.Column(db.String(20), nullable=False)     # Type: ['admin', 'staff', 'student']
    staffId = db.relationship('Staffs', backref='Users', lazy=True)
    studentId = db.relationship('Students', backref='Users', lazy=True)

    def __repr__(self):
        return f"Users('{self.id}', '{self.email}, '{self.type}'')"


class Staffs(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    employeeNo = db.Column(db.String(20), nullable=False)
    role = db.Column(db.String(20), nullable=False)     # Role: ['lab technician', 'professor']
    userId = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    def __repr__(self):
        return f"Staffs('{self.id}, {self.name}, {self.employeeNo}, {self.role}, {self.userId}')"


class Students(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    matricNo = db.Column(db.String(10), nullable=False)
    userId = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
