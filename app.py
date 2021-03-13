import base64

from flask import url_for, render_template, redirect, request, flash, jsonify
from flask_bcrypt import check_password_hash, generate_password_hash
from flask_login import login_user, current_user, login_required, logout_user
from flask_mail import Message

import csv
import values
import datetime
import os
from facial_recognition import recognize
from forms import LoginForm, RegistrationForm, AdminAddFileForm, ManualAttendanceForm
from models import app, db, Users, Staffs, Students, Courses, Indexes, StaffInCharged, IndexDates, Attendance, mail


def get_dashboard():
    dashboard_data = values.dashboards['admin'] if current_user.role == 'admin' else \
        values.dashboards['staff']
    return dashboard_data


@app.route('/', methods=['GET', 'POST'])
@app.route('/index', methods=['GET', 'POST'])
def index():
    form = LoginForm()
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if form.validate_on_submit():
        user = Users.query.filter_by(email=form.email.data.casefold()).first()
        if user and check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('dashboard'))
        else:
            flash('Login Unsuccessful. Please check email and password', 'danger')
    return render_template('index.html', form=form, title='Login')


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/register_account', methods=['GET', 'POST'])
@login_required
def register_account():
    if current_user.role != 'admin':
        flash('You are not authorized to perform this action', 'danger')
        return redirect(url_for('dashboard'))

    dashboard_data = get_dashboard()
    form = RegistrationForm()

    if form.validate_on_submit():
        appointment = 'staff'
        hashed_password = generate_password_hash(form.password.data).decode('utf-8')
        user = Users(email=form.email.data.casefold(), password=hashed_password, role=appointment)
        db.session.add(user)
        db.session.commit()
        person = Staffs(name=form.name.data, employeeNo=form.personNo.data,
                        role=form.appointment.data.casefold(), userId=user.id)
        db.session.add(person)
        db.session.commit()

        flash('A staff account has been created', 'success')
        return redirect(url_for('dashboard'))
    return render_template('register_account.html', form=form, title='Register', dashboard_data=dashboard_data)


@app.route('/dashboard')
@login_required
def dashboard():
    dashboard_data = get_dashboard()
    return render_template('dashboard.html', dashboard_data=dashboard_data, title="Dashboard")


def find_student(matric_no):
    return Students.query.filter_by(matricNo=matric_no).first()


@app.route('/add_student', methods=['GET', 'POST'])
@login_required
def add_student():
    if current_user.role != 'admin':
        flash('You are not authorized to perform this action', 'danger')
        return redirect(url_for('dashboard'))

    dashboard_data = get_dashboard()
    form = AdminAddFileForm()

    if form.validate_on_submit():
        added = False
        file = form.fileInput.data
        file_string = str(file.read(), 'utf-8')
        student_dict = csv.DictReader(file_string.splitlines(), skipinitialspace=True)
        for student_details in student_dict:
            try:
                student = find_student(student_details['matricNo'])
                if student is None:  # Add the student if it is not inside the database
                    added = True
                    student = Students(name=student_details['name'], matricNo=student_details['matricNo'],
                                       email=student_details['email'])
                    db.session.add(student)
            except:
                flash('CSV contains incorrect fields', 'danger')
                return redirect(url_for('dashboard'))

        if added:
            db.session.commit()
            flash('Student details have been added', 'success')
        else:
            flash('No student details was added', 'info')
        return redirect(url_for('dashboard'))

    return render_template('admin_add_file.html', form=form, dashboard_data=dashboard_data, legend='Add Student')


def find_course(course_code):
    return Courses.query.filter_by(courseCode=course_code).first()


def find_index(index_id):
    return Indexes.query.filter_by(indexId=index_id).first()


def get_course_id(course_code):
    return Courses.query.filter_by(courseCode=course_code).first()


def get_staff(staff_employee_id):
    return Staffs.query.filter_by(employeeNo=staff_employee_id).first()


def find_staff_in_charged(index_id, staff_id):
    return StaffInCharged.query.filter_by(indexId=index_id, staffId=staff_id).first()


def find_index_date(index_id, date):
    return IndexDates.query.filter_by(indexId=index_id, date=date).first()


@app.route('/upload_course', methods=['GET', 'POST'])
@login_required
def upload_course():
    if current_user.role != 'admin':
        flash('You are not authorized to perform this action', 'danger')
        return redirect(url_for('dashboard'))

    dashboard_data = get_dashboard()
    form = AdminAddFileForm()

    if form.validate_on_submit():
        added = False
        file = form.fileInput.data
        file_string = str(file.read(), 'utf-8')
        course_dict = csv.DictReader(file_string.splitlines(), skipinitialspace=True)
        for course_details in course_dict:
            try:
                course = find_course(course_details['courseCode'])
                if course is None:  # Add the course if it is not inside the database
                    added = True
                    course = Courses(name=course_details['name'], courseCode=course_details['courseCode'])
                    db.session.add(course)

                course_index = find_index(course_details['index'])
                if course_index is None:
                    added = True
                    course_index = Indexes(indexId=course_details['index'], className=course_details['className'],
                                           courseId=get_course_id(course_details['courseCode']).id)
                    db.session.add(course_index)

                date_obj = datetime.datetime.strptime(course_details['date'], '%d/%m/%Y')
                index_date = find_index_date(course_index.indexId, date_obj)
                if index_date is None:
                    added = True
                    index_date = IndexDates(date=date_obj, indexId=course_index.indexId)
                    db.session.add(index_date)

                staff = get_staff(course_details['staffInCharged'])
                if staff is None:
                    flash(f'{course_details["staffInCharged"]} is not inside the database. Please add this staff first',
                          'danger')
                    return redirect(url_for('dashboard'))

                staff_in_charged = find_staff_in_charged(course_details['index'], staff.id)
                if staff_in_charged is None:
                    added = True
                    staff_in_charged = StaffInCharged(indexId=course_details['index'], staffId=staff.id)
                    db.session.add(staff_in_charged)
            except:
                flash('CSV contains incorrect fields', 'danger')
                return redirect(url_for('dashboard'))

        if added:
            db.session.commit()
            flash('Course details have been added', 'success')
        else:
            flash('No course details was added', 'info')
        return redirect(url_for('dashboard'))

    return render_template('admin_add_file.html', form=form, dashboard_data=dashboard_data, legend='Upload Course')


def get_all_index_dates(index_id):
    return IndexDates.query.filter_by(indexId=index_id)


def find_attendance(index_date_id, student_id):
    return Attendance.query.filter_by(indexDateId=index_date_id, studentId=student_id).first()


@app.route('/upload_class', methods=['GET', 'POST'])
@login_required
def upload_class():
    if current_user.role != 'admin':
        flash('You are not authorized to perform this action', 'danger')
        return redirect(url_for('dashboard'))

    dashboard_data = get_dashboard()
    form = AdminAddFileForm()

    if form.validate_on_submit():
        added = False
        file = form.fileInput.data
        file_string = str(file.read(), 'utf-8')
        class_dict = csv.DictReader(file_string.splitlines(), skipinitialspace=True)
        for class_details in class_dict:
            try:
                course_index = find_index(class_details['index'])
                if course_index is None:
                    flash(f'Index {class_details["index"]} is not inside the database. Please add this course first',
                          'danger')
                    return redirect(url_for('dashboard'))

                student = find_student(class_details['matricNo'])
                if student is None:
                    flash(
                        f'Student {class_details["matricNo"]} is not inside the database. Please add this student first',
                        'danger')
                    return redirect(url_for('dashboard'))

                index_dates = get_all_index_dates(course_index.indexId)
                for index_date in index_dates:
                    attendance = find_attendance(index_date.id, student.id)
                    if attendance is None:
                        added = True
                        attendance = Attendance(indexDateId=index_date.id, studentId=student.id)
                        db.session.add(attendance)
            except:
                flash('CSV contains incorrect fields', 'danger')
                return redirect(url_for('dashboard'))

        if added:
            db.session.commit()
            flash('Class details have been added', 'success')
        else:
            flash('No class details was added', 'info')
        return redirect(url_for('dashboard'))

    return render_template('admin_add_file.html', form=form, dashboard_data=dashboard_data, legend='Upload Class')


@app.route('/view_classes')
@login_required
def view_classes():
    if current_user.role != 'staff':
        flash('You are not authorized to perform this action', 'danger')
        return redirect(url_for('dashboard'))

    dashboard_data = get_dashboard()
    indexes_in_charged = current_user.staff[0].indexesInCharge

    return render_template('view_classes.html', classes=indexes_in_charged, dashboard_data=dashboard_data)


@app.route('/view_class_dates/<int:class_index>')
@login_required
def view_class_dates(class_index):
    if current_user.role != 'staff':
        flash('You are not authorized to perform this action', 'danger')
        return redirect(url_for('dashboard'))

    dashboard_data = get_dashboard()
    class_dates = IndexDates.query.filter_by(indexId=class_index).all()

    return render_template('view_class_dates.html', dashboard_data=dashboard_data,
                           course_code=class_dates[0].index.course.courseCode,
                           class_name=class_dates[0].index.className, class_dates=class_dates)


@app.route('/view_attendance/<int:class_date_id>')
@login_required
def view_attendance(class_date_id):
    if current_user.role != 'staff':
        flash('You are not authorized to perform this action', 'danger')
        return redirect(url_for('dashboard'))

    prof = True if current_user.staff[0].role == "professor" else False
    dashboard_data = get_dashboard()
    attendances = Attendance.query.filter_by(indexDateId=class_date_id).all()
    attendance_started = IndexDates.query.get(class_date_id).attendance_started

    return render_template('view_attendance.html', dashboard_data=dashboard_data, attendances=attendances,
                           date=attendances[0].indexDate.date, class_name=attendances[0].indexDate.index.className,
                           prof=prof, class_date_id=class_date_id, attendance_started=attendance_started)


@app.route('/edit_attendance/<int:class_date_id>', methods=['GET', 'POST'])
@login_required
def edit_attendance(class_date_id):
    if current_user.role != 'staff':
        flash('You are not authorized to perform this action', 'danger')
        return redirect(url_for('dashboard'))

    attendances = Attendance.query.filter_by(indexDateId=class_date_id).all()

    if request.method == "POST":
        for attend in attendances:
            attend.attendance = request.form[f'attendance_{attend.id}']
        db.session.commit()
        flash('Successfully changed the attendance', 'success')
        return redirect(url_for('view_attendance', class_date_id=class_date_id))

    prof = True if current_user.staff[0].role == "professor" else False
    dashboard_data = get_dashboard()


    return render_template('edit_attendance.html', dashboard_data=dashboard_data, attendances=attendances,
                           date=attendances[0].indexDate.date, class_name=attendances[0].indexDate.index.className,
                           prof=prof)


@app.route('/send_absentee_email/<int:class_date_id>')
@login_required
def send_absentee_email(class_date_id):
    if current_user.role != 'staff' or current_user.staff[0].role != 'professor':
        flash('You are not authorized to perform this action', 'danger')
        return redirect(url_for('dashboard'))

    class_date = IndexDates.query.get(class_date_id)

    if not class_date.attendance_started:
        attendances = Attendance.query.filter_by(indexDateId=class_date_id).all()
        email_sent = False
        for attend in attendances:
            if attend.attendance == 'Absent':
                email_sent = True
                send_absent_email(attend.student.email, class_date)
        if email_sent:
            flash('Email has been sent to the absentee', 'success')
        else:
            flash('No email was sent to the absentee', 'warning')
    else:
        flash('Please stop the attendance taking process before sending absentees email', 'warning')

    return redirect(url_for('view_attendance', class_date_id=class_date_id))


def send_absent_email(email, class_date):
    msg = Message('Attendance Warning',
                  sender="noreply@demo.com", recipients=[email])
    msg.body = f''' Dear Student,
    
Please be informed that you did not attend the following lesson
Class: {class_date.index.course.courseCode} - {class_date.index.className}
Date: {class_date.date.strftime("%d/%m/%Y")}

If you have a valid MC, please email the MC to your tutor.
Otherwise, your attendance will be absent.

Thank you.

Regards
Face It System    
'''

    mail.send(msg)


@app.route('/start_attendance/<int:class_date_id>')
@login_required
def start_attendance(class_date_id):
    if current_user.role != 'staff':
        flash('You are not authorized to perform this action', 'danger')
        return redirect(url_for('dashboard'))

    class_index = IndexDates.query.filter_by(id=class_date_id).first().index

    # Check if there is an existing attendance started for current class
    has_started = False
    for class_date in class_index.dates:
        if class_date.attendance_started:
            has_started = True
            break

    if has_started:
        flash('Please stop the existing attendance before starting new one for this class', 'warning')
    else:
        IndexDates.query.filter_by(id=class_date_id).first().attendance_started = True
        db.session.commit()
        flash('Successfully started the attendance', 'success')
    return redirect(url_for('view_class_dates', class_index=class_index.indexId))


@app.route('/stop_attendance/<int:class_date_id>')
@login_required
def stop_attendance(class_date_id):
    if current_user.role != 'staff':
        flash('You are not authorized to perform this action', 'danger')
        return redirect(url_for('dashboard'))

    class_date = IndexDates.query.filter_by(id=class_date_id).first()
    class_date.attendance_started = False
    db.session.commit()
    flash('Successfully stopped the attendance', 'success')
    return redirect(url_for('view_class_dates', class_index=class_date.index.indexId))


@app.route('/take_attendance/<int:class_date_id>', methods=['GET', 'POST'])
def take_attendance(class_date_id):
    attendances = Attendance.query.filter_by(indexDateId=class_date_id).all()

    form = ManualAttendanceForm()
    attendance_started = attendances[0].indexDate.attendance_started
    if attendance_started:
        if form.validate_on_submit():
            taken = False
            for attend in attendances:
                if attend.student.matricNo == form.matricNo.data.upper():
                    taken = True
                    if attend.attendance != 'Present':
                        attend.attendance = 'Present'
                        db.session.commit()
                        flash(f"Attendance has been taken for Student {form.matricNo.data.upper()}", "success")
                    else:
                        flash(f"Attendance was already taken for Student {form.matricNo.data.upper()}", "info")
            if not taken:
                flash(f"Unable to take attendance for Student {form.matricNo.data.upper()}", "danger")
            form.matricNo.data = ""
        return render_template('take_attendance.html', attendances=attendances,
                               date=attendances[0].indexDate.date, class_name=attendances[0].indexDate.index.className,
                               class_date_id=class_date_id, form=form)
    else:
        flash('The attendance taking for this class has not started', 'warning')
        return redirect(url_for('error'))


@app.route('/error')
def error():
    return render_template('error.html')


@app.route('/take_photo/<int:class_date_id>')
def take_photo(class_date_id):
    return render_template('take_photo.html', class_date_id=class_date_id)


@app.route('/facial_recognition/<int:class_date_id>')
def facial_recognition(class_date_id):
    photo_base64 = request.args.get('photo_cap')
    header, encoded = photo_base64.split(",", 1)
    binary_data = base64.b64decode(encoded)
    image_name = "photo.jpg"

    with open(f"facial_recognition/image/{image_name}", "wb") as f:
    # with open(os.path.join("D:\\Python Projects\\flask-project\\frats\\facial_recognition\\image",
    #                        image_name), "wb") as f:
        f.write(binary_data)

    result = recognize.recognize_image()
    print(result)

    return jsonify(result=result, class_date_id=class_date_id)


@app.route('/facial_recognition_attendance/<int:class_date_id>/<string:matricNo>')
def facial_recognition_attendance(class_date_id, matricNo):
    attendances = Attendance.query.filter_by(indexDateId=class_date_id).all()

    attendance_started = attendances[0].indexDate.attendance_started
    taken = False
    if attendance_started:
        for attend in attendances:
            if attend.student.matricNo == matricNo:
                taken = True
                if attend.attendance != "Present":
                    attend.attendance = "Present"
                    db.session.commit()
                    flash(f"Attendance has been taken for Student {matricNo}", "success")
                else:
                    flash(f"Attendance was already taken for Student {matricNo}", "info")
        if not taken:
            flash(f"Unable to take attendance for Student {matricNo}", "danger")
        return redirect(url_for('take_attendance', class_date_id=class_date_id))
    else:
        flash('The attendance taking for this class has not started', 'warning')
        return redirect(url_for('error'))


@app.route('/wrong_image/<int:class_date_id>')
def wrong_image(class_date_id):
    flash(f"Unable to take attendance using facial recognition. Please use manual attendance", 'warning')
    return redirect(url_for('take_attendance', class_date_id=class_date_id))


if __name__ == '__main__':
    app.run(debug=True)
