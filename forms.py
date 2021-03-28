from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SelectField, SubmitField, IntegerField
from wtforms.validators import InputRequired, Email, Length, EqualTo, ValidationError
from flask_wtf.file import FileField, FileRequired, FileAllowed
from models import Users, Students


class LoginForm(FlaskForm):
    email = StringField('Email', validators=[InputRequired(),
                                             Email(message='Invalid Email'),
                                             Length(max=50)])
    password = PasswordField('Password', validators=[InputRequired(),
                                                    Length(min=8, max=16)])
    remember = BooleanField('Remember Me')
    submit = SubmitField('Login')


class RegistrationForm(FlaskForm):
    email = StringField('Email', validators=[InputRequired(),
                                             Email(message='Invalid email'),
                                             Length(max=50)])
    personNo = StringField('Employee Number', validators=[InputRequired(),
                                                            Length(max=16)])
    name = StringField('Name', validators=[InputRequired(),
                                           Length(max=80)])
    password = PasswordField('Password', validators=[InputRequired(),
                                                     Length(min=8, max=16)])
    confirm_password = PasswordField('Confirm Password', validators=[InputRequired(),
                                                                    EqualTo('password')])
    appointment = SelectField('Appointment', choices=[('Professor', 'Professor'),
                                                      ('Lab Technician', 'Lab Technician')])
    submit = SubmitField('Register')

    def validate_email(self, email):
        user = Users.query.filter_by(email=email.data.casefold()).first()
        if user:
            raise ValidationError("That email exists inside the database. Please choose a different one.")

        email_validation = email.data.casefold().split('@')
        if email_validation[1] != 'e.ntu.edu.sg':
            raise ValidationError("Please use NTU email.")


class StudentRegistrationForm(FlaskForm):
    name = StringField('Name', validators=[InputRequired(),
                                           Length(max=80)])
    matricNo = StringField('Matric Number', validators=[InputRequired(),
                                                            Length(max=16)])
    email = StringField('Email', validators=[InputRequired(),
                                             Email(message='Invalid email'),
                                             Length(max=50)])
    submit = SubmitField('Add Student')

    def validate_email(self, email):
        student = Students.query.filter_by(email=email.data.casefold()).first()
        if student:
            raise ValidationError("That email exists inside the database.")

        email_validation = email.data.casefold().split('@')
        if email_validation[1] != 'e.ntu.edu.sg':
            raise ValidationError("Please use NTU email.")


class AdminAddFileForm(FlaskForm):
    fileInput = FileField('Please upload the details in a CSV file',
                          validators=[FileRequired(), FileAllowed(['csv'], 'CSV File Only!')])
    submit = SubmitField('Submit')


class ManualAttendanceForm(FlaskForm):
    matricNo = StringField('matric no',
                           validators=[InputRequired(), Length(max=9)],
                           render_kw={"placeholder":"U1234567A"})
    submit = SubmitField('Confirm')


class AddStudentToClassForm(FlaskForm):
    students = Students.query.all()
    seatNo = IntegerField("Seat No", validators=[InputRequired()])
    name = SelectField("Student Name")
