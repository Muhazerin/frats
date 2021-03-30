from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin
from flask_bcrypt import Bcrypt
from flask_mail import Mail

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
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get('EMAIL_USER')
app.config['MAIL_PASSWORD'] = os.environ.get('EMAIL_PASS')
mail = Mail(app)


@login_manager.user_loader
def load_user(user_id):
    return Users.query.get(int(user_id))


# The users of this system are NTU staffs
class Users(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    role = db.Column(db.String(20), nullable=False)     # Role: ['admin', 'staff']
    staff = db.relationship('Staffs', cascade='delete, delete-orphan', backref='user', lazy=True)

    def __repr__(self):
        return f"Users('{self.id}', '{self.email}', '{self.role}')"


# The staffs of this system are the Prof, TA, Lab Tech
class Staffs(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    employeeNo = db.Column(db.String(20), unique=True, nullable=False)
    role = db.Column(db.String(20), nullable=False)     # Role: ['lab technician', 'professor']
    userId = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    indexesInCharge = db.relationship('StaffInCharged', cascade='delete, delete-orphan', backref='staff', lazy=True)

    def __repr__(self):
        return f"Staffs('{self.id}, {self.name}, {self.employeeNo}, {self.role}, {self.userId}')"


# The students are NTU students
class Students(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    matricNo = db.Column(db.String(10), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    attendances = db.relationship('Attendance', cascade='delete, delete-orphan', backref='student', lazy=True)

    def __repr__(self):
        return f"Student('{self.id}', '{self.name}', '{self.matricNo}', '{self.email}')"


# The Courses in NTU
class Courses(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    courseCode = db.Column(db.String(10), nullable=False)
    indexes = db.relationship('Indexes', cascade='delete, delete-orphan', backref='course', lazy=True)

    def __repr__(self):
        return f"Course('{self.id}', '{self.name}', '{self.courseCode}')"


# The different indexes belonging to a course
class Indexes(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    indexId = db.Column(db.Integer, nullable=False)
    className = db.Column(db.String(5), nullable=False)
    room = db.Column(db.Integer, nullable=False)
    courseId = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    staffInCharged = db.relationship('StaffInCharged', cascade='delete, delete-orphan', backref='index', lazy=True)
    dates = db.relationship('IndexDates', cascade='delete, delete-orphan', backref='index', lazy=True)

    def __repr__(self):
        return f"Indexes('{self.id}', '{self.indexId}', '{self.course.name}')"


# The staff that is in charged of a particular index
class StaffInCharged(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    indexId = db.Column(db.Integer, db.ForeignKey('indexes.id'), nullable=False)
    staffId = db.Column(db.Integer, db.ForeignKey('staffs.id'), nullable=False)

    def __repr__(self):
        return f"StaffInCharged('{self.id}', '{self.indexId}', '{self.staff.name}')"


# This is the table for the class date (E.g 26 Jan, 9 Feb, 23 Feb for index 10173)
class IndexDates(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime, nullable=False)
    attendance_started = db.Column(db.Boolean, default=False, nullable=False)
    indexId = db.Column(db.Integer, db.ForeignKey('indexes.id'), nullable=False)
    attendance = db.relationship('Attendance', cascade='delete, delete-orphan', backref='indexDate', lazy=True)

    def __repr__(self):
        return f"IndexDates('{self.id}', '{self.indexId}', '{self.date}')"


#
class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    indexDateId = db.Column(db.Integer, db.ForeignKey('index_dates.id'), nullable=False)
    studentId = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    seatNo = db.Column(db.Integer, nullable=False)
    attendance = db.Column(db.String(10), default='Absent', nullable=False)   # Absent/Present

    def __repr__(self):
        return f"Attendance('{self.id}', '{self.indexDate.indexId}', '{self.indexDate.date}', " \
               f"'{self.student.name}', '{self.attendance}')"
