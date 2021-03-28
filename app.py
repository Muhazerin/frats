import base64

from flask import Flask
from flask import url_for, render_template, redirect, request, flash, jsonify
from flask_bcrypt import check_password_hash, generate_password_hash
from flask_login import login_user, current_user, login_required, logout_user
from flask_mail import Message

import csv
import values
import datetime
import os
from facial_recognition import recognize
from forms import LoginForm, RegistrationForm, AdminAddFileForm, ManualAttendanceForm, StudentRegistrationForm
from models import app, db, Users, Staffs, Students, Courses, Indexes, StaffInCharged, IndexDates, Attendance, mail


def get_dashboard():
    dashboard_data = values.dashboards['admin'] if current_user.role == 'admin' else \
        values.dashboards['staff']
    return dashboard_data


def find_account(acc_email):
    return Users.query.filter_by(email=acc_email).first()


@app.route('/', methods=['GET', 'POST'])
@app.route('/index', methods=['GET', 'POST'])
def index():
    form = LoginForm()
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if form.validate_on_submit():
        user = Users.query.filter_by(email=form.email.data).first()
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


@app.route('/manage_account')
@login_required
def manage_account():
    if current_user.role != 'admin':
        flash('You are not authorized to perform this action', 'danger')
        return redirect(url_for('dashboard'))

    dashboard_data = get_dashboard()
    accounts = Users.query.filter_by(role='staff').all()
    return render_template('manage_account.html', dashboard_data=dashboard_data, accounts=accounts)


@app.route('/register_one_account', methods=['GET', 'POST'])
@login_required
def register_one_account():
    if current_user.role != 'admin':
        flash('You are not authorized to perform this action', 'danger')
        return redirect(url_for('dashboard'))

    dashboard_data = get_dashboard()
    form = RegistrationForm()

    if form.validate_on_submit():
        appointment = 'staff'
        hashed_password = generate_password_hash(form.password.data).decode('utf-8')
        user = Users(email=form.email.data, password=hashed_password, role=appointment)
        db.session.add(user)
        db.session.commit()
        person = Staffs(name=form.name.data, employeeNo=form.personNo.data,
                        role=form.appointment.data.casefold(), userId=user.id)
        db.session.add(person)
        db.session.commit()

        flash('A staff account has been created', 'success')
        return redirect(url_for('manage_account'))
    return render_template('register_one_account.html', form=form, title='Register', dashboard_data=dashboard_data)


@app.route('/register_account', methods=['GET', 'POST'])
@login_required
def register_account():
    if current_user.role != 'admin':
        flash('You are not authorized to perform this action', 'danger')
        return redirect(url_for('dashboard'))

    dashboard_data = get_dashboard()
    form = AdminAddFileForm()

    if form.validate_on_submit():
        added = False
        file = form.fileInput.data
        file_string = str(file.read(), 'utf-8')
        account_dict = csv.DictReader(file_string.splitlines(), skipinitialspace=True)
        for account_details in account_dict:
            try:
                account = find_account(account_details['email'])
                if account is None:
                    added = True
                    hashed_password = generate_password_hash(account_details['password']).decode('utf-8')
                    account = Users(email=account_details['email'], password=hashed_password,
                                    role='staff')
                    db.session.add(account)
                    db.session.commit()

                    staff = Staffs(name=account_details['name'], employeeNo=account_details['employeeNo'],
                                   role=account_details['role'], userId=account.id)
                    db.session.add(staff)
                    db.session.commit()
            except:
                flash('CSV contains incorrect fields', 'danger')
                return redirect(url_for('manage_account'))

        if added:
            flash('Account(s) have been added', 'success')
        else:
            flash('No accounts were added', 'info')
        return redirect(url_for('manage_account'))

    return render_template('admin_add_file.html', form=form, dashboard_data=dashboard_data, legend='Register Accounts')


@app.route('/edit_account', methods=['GET', 'POST'])
@login_required
def edit_account():
    if current_user.role != 'admin':
        flash('You are not authorized to perform this action', 'danger')
        return redirect(url_for('dashboard'))

    dashboard_data = get_dashboard()
    accounts = Users.query.filter_by(role='staff').all()

    if request.method == "POST":
        valid = True
        for account in accounts:
            # validate the emails in the first pass
            email_validation = request.form[f'email_{account.id}'].split('@')
            if email_validation[1] != 'e.ntu.edu.sg':
                flash(f'{request.form[f"email_{account.id}"]} is not a valid NTU email', 'danger')
                valid = False
                break
        if valid:
            for account in accounts:
                # insert into database at second pass
                account.staff[0].name = request.form[f'name_{account.id}']
                account.email = request.form[f'email_{account.id}']
                account.staff[0].employeeNo = request.form[f'employeeNo_{account.id}']
                account.staff[0].role = request.form[f'role_{account.id}']
            db.session.commit()
            flash('Successfully edited the accounts', 'success')
            return redirect(url_for('manage_account'))

    return render_template('edit_account.html', accounts=accounts, dashboard_data=dashboard_data)


@app.route('/remove_account', methods=['GET', 'POST'])
@login_required
def remove_account():
    if current_user.role != 'admin':
        flash('You are not authorized to perform this action', 'danger')
        return redirect(url_for('dashboard'))

    dashboard_data = get_dashboard()
    accounts = Users.query.filter_by(role='staff').all()

    if request.method == "POST":
        remove_list = request.form.getlist('remove')
        if remove_list:
            for acc_id in remove_list:
                db.session.delete(Users.query.get(acc_id))
            db.session.commit()
            flash('Account(s) were removed', 'success')
            return redirect(url_for('manage_account'))
        flash('No account were removed', 'warning')
        return redirect(url_for('manage_account'))

    return render_template('remove_account.html', accounts=accounts, dashboard_data=dashboard_data)


@app.route('/dashboard')
@login_required
def dashboard():
    dashboard_data = get_dashboard()
    return render_template('dashboard.html', dashboard_data=dashboard_data, title="Dashboard")


def find_student(matric_no):
    return Students.query.filter_by(matricNo=matric_no).first()


@app.route('/manage_student')
@login_required
def manage_student():
    if current_user.role != 'admin':
        flash('You are not authorized to perform this action', 'danger')
        return redirect(url_for('dashboard'))

    dashboard_data = get_dashboard()
    students = Students.query.all()
    return render_template('manage_students.html', students=students, dashboard_data=dashboard_data)


@app.route('/add_one_student', methods=['GET', 'POST'])
@login_required
def add_one_student():
    if current_user.role != 'admin':
        flash('You are not authorized to perform this action', 'danger')
        return redirect(url_for('dashboard'))

    dashboard_data = get_dashboard()
    form = StudentRegistrationForm()

    if form.validate_on_submit():
        student = Students(name=form.name.data, matricNo=form.matricNo.data, email=form.email.data)
        db.session.add(student)
        db.session.commit()
        flash('Student has been created', 'success')
        return redirect(url_for('manage_student'))

    return render_template('add_one_student.html', form=form, dashboard_data=dashboard_data)


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
                return redirect(url_for('manage_student'))

        if added:
            db.session.commit()
            flash('Student details have been added', 'success')
        else:
            flash('No student details was added', 'info')
        return redirect(url_for('manage_student'))

    return render_template('admin_add_file.html', form=form, dashboard_data=dashboard_data, legend='Add Student')


@app.route('/edit_student', methods=['GET', 'POST'])
@login_required
def edit_student():
    if current_user.role != 'admin':
        flash('You are not authorized to perform this action', 'danger')
        return redirect(url_for('dashboard'))

    dashboard_data = get_dashboard()
    students = Students.query.all()

    if request.method == "POST":
        valid = True
        for student in students:
            student.name = request.form[f'name_{student.id}']
        db.session.commit()
        flash('Successfully edited students', 'success')
        return redirect(url_for('manage_student'))

    return render_template('edit_student.html', students=students, dashboard_data=dashboard_data)


@app.route('/remove_student', methods=['GET', 'POST'])
@login_required
def remove_student():
    if current_user.role != 'admin':
        flash('You are not authorized to perform this action', 'danger')
        return redirect(url_for('dashboard'))

    dashboard_data = get_dashboard()
    students = Students.query.all()

    if request.method == "POST":
        remove_list = request.form.getlist('remove')
        if remove_list:
            for student_id in remove_list:
                db.session.delete(Students.query.get(student_id))
            db.session.commit()
            flash('Student(s) details were removed', 'success')
            return redirect(url_for('manage_student'))
        flash('No student details were removed', 'warning')
        return redirect(url_for('manage_student'))

    return render_template('remove_student.html', students=students, dashboard_data=dashboard_data)


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


@app.route('/manage_course')
@login_required
def manage_course():
    if current_user.role != 'admin':
        flash('You are not authorized to perform this action', 'danger')
        return redirect(url_for('dashboard'))

    dashboard_data = get_dashboard()
    courses = Courses.query.all()
    return render_template('manage_courses.html', courses=courses, dashboard_data=dashboard_data)


@app.route('/view_course_index/<int:course_id>')
def view_course_index(course_id):
    if current_user.role != 'admin':
        flash('You are not authorized to perform this action', 'danger')
        return redirect(url_for('dashboard'))

    dashboard_data = get_dashboard()
    indexes = Indexes.query.filter_by(courseId=course_id).all()
    class_dates = []
    for an_index in indexes:
        temp_dates = []
        for i_date in an_index.dates:
            temp_dates.append(i_date.date.strftime("%d/%m/%Y"))
        class_dates.append(temp_dates)

    print(class_dates)
    return render_template('view_course_index.html', course_code=indexes[0].course.courseCode, indexes=indexes,
                           class_dates=class_dates, dashboard_data=dashboard_data)


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
                                           room=course_details['room'],
                                           courseId=get_course_id(course_details['courseCode']).id)
                    db.session.add(course_index)

                date_obj = datetime.datetime.strptime(course_details['date'], '%d/%m/%Y')
                index_date = find_index_date(course_index.id, date_obj)
                if index_date is None:
                    added = True
                    index_date = IndexDates(date=date_obj, indexId=course_index.id)
                    db.session.add(index_date)

                staff = get_staff(course_details['staffInCharged'])
                if staff is None:
                    flash(f'{course_details["staffInCharged"]} is not inside the database. Please add this staff first',
                          'danger')
                    return redirect(url_for('manage_course'))

                staff_in_charged = find_staff_in_charged(course_index.id, staff.id)
                if staff_in_charged is None:
                    added = True
                    staff_in_charged = StaffInCharged(indexId=course_index.id, staffId=staff.id)
                    db.session.add(staff_in_charged)
            except:
                flash('CSV contains incorrect fields', 'danger')
                return redirect(url_for('manage_course'))

        if added:
            db.session.commit()
            flash('Course details have been added', 'success')
        else:
            flash('No course details was added', 'info')
        return redirect(url_for('manage_course'))

    return render_template('admin_add_file.html', form=form, dashboard_data=dashboard_data, legend='Upload Course')


@app.route('/remove_course', methods=['GET', 'POST'])
def remove_course():
    if current_user.role != 'admin':
        flash('You are not authorized to perform this action', 'danger')
        return redirect(url_for('dashboard'))

    dashboard_data = get_dashboard()
    courses = Courses.query.all()

    if request.method == "POST":
        remove_list = request.form.getlist('remove')
        if remove_list:
            for course_id in remove_list:
                db.session.delete(Courses.query.get(course_id))
            db.session.commit()
            flash('Course(s) were removed', 'success')
            return redirect(url_for('manage_course'))
        flash('No course were removed', 'info')
        return redirect(url_for('manage_course'))

    return render_template('remove_course.html', courses=courses, dashboard_data=dashboard_data)


@app.route('/remove_all_courses', methods=['GET', 'POST'])
@login_required
def remove_all_courses():
    if current_user.role != 'admin':
        flash('You are not authorized to perform this action', 'danger')
        return redirect(url_for('dashboard'))

    courses = Courses.query.all()
    if courses:
        for course in courses:
            db.session.delete(course)
        db.session.commit()
        flash('Successfully removed all courses', 'success')
    else:
        flash('No courses were removed', 'info')

    return redirect(url_for('manage_course'))


def get_all_index_dates(index_id):
    return IndexDates.query.filter_by(indexId=index_id)


def find_attendance(index_date_id, student_id):
    return Attendance.query.filter_by(indexDateId=index_date_id, studentId=student_id).first()


@app.route('/manage_class')
@login_required
def manage_class():
    if current_user.role != 'admin':
        flash('You are not authorized to perform this action', 'danger')
        return redirect(url_for('dashboard'))

    dashboard_data = get_dashboard()
    classes = Indexes.query.all()
    class_dates = []
    for a_class in classes:
        temp_dates = []
        for i_date in a_class.dates:
            temp_dates.append(i_date.date.strftime("%d/%m/%Y"))
        class_dates.append(temp_dates)

    return render_template('manage_classes.html', classes=classes, class_dates=class_dates,
                           dashboard_data=dashboard_data)


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
                    return redirect(url_for('manage_class'))

                student = find_student(class_details['matricNo'])
                if student is None:
                    flash(
                        f'Student {class_details["matricNo"]} is not inside the database. Please add this student first',
                        'danger')
                    return redirect(url_for('manage_class'))

                index_dates = get_all_index_dates(course_index.id)
                for index_date in index_dates:
                    attendance = find_attendance(index_date.id, student.id)
                    if attendance is None:
                        added = True
                        attendance = Attendance(indexDateId=index_date.id, studentId=student.id,
                                                seatNo=class_details['seatNo'])
                        db.session.add(attendance)
            except:
                flash('CSV contains incorrect fields', 'danger')
                return redirect(url_for('manage_class'))

        if added:
            db.session.commit()
            flash('Class details have been added', 'success')
        else:
            flash('No class details was added', 'info')
        return redirect(url_for('manage_class'))

    return render_template('admin_add_file.html', form=form, dashboard_data=dashboard_data, legend='Upload Class')


@app.route('/view_class_student/<int:index_id>')
@login_required
def view_class_students(index_id):
    if current_user.role != 'admin':
        flash('You are not authorized to perform this action', 'danger')
        return redirect(url_for('dashboard'))

    dashboard_data = get_dashboard()
    attendances = Indexes.query.get(index_id).dates[0].attendance
    if attendances:
        course_code = attendances[0].indexDate.index.course.courseCode
        class_name = attendances[0].indexDate.index.className

        return render_template('view_class_students.html', attendances=attendances, dashboard_data=dashboard_data,
                               course_code=course_code, class_name=class_name, index_id=index_id)
    else:
        flash('No students enrolled in this class', 'warning')
        return redirect(url_for('manage_class'))


@app.route('/remove_students/<int:index_id>', methods=['GET', 'POST'])
@login_required
def remove_students(index_id):
    if current_user.role != 'admin':
        flash('You are not authorized to perform this action', 'danger')
        return redirect(url_for('dashboard'))

    dashboard_data = get_dashboard()
    attendances = Indexes.query.get(index_id).dates[0].attendance
    course_code = attendances[0].indexDate.index.course.courseCode
    class_name = attendances[0].indexDate.index.className

    if request.method == "POST":
        remove_list = request.form.getlist('remove')
        if remove_list:
            index_dates = Indexes.query.get(index_id).dates
            for student_id in remove_list:
                for index_date in index_dates:
                    removed_entry = Attendance.query.filter_by(studentId=student_id, indexDateId=index_date.id).first()
                    db.session.delete(removed_entry)
            db.session.commit()
            flash('Student was removed from the class', 'success')
            return redirect(url_for('view_class_students', index_id=index_id))
        flash('No student was removed from this class', 'info')
        return redirect(url_for('view_class_students', index_id=index_id))

    return render_template('remove_class_students.html', attendances=attendances, dashboard_data=dashboard_data,
                           course_code=course_code, class_name=class_name)


# highest seat
def get_highest_seat_no(index_date):
    highest = 1
    for attendance in index_date.attendance:
        if attendance.seatNo >= highest:
            highest = attendance.seatNo + 1
    return highest


@app.route('/add_student_to_class/<int:index_id>', methods=['GET', 'POST'])
@login_required
def add_student_to_class(index_id):
    if current_user.role != 'admin':
        flash('You are not authorized to perform this action', 'danger')
        return redirect(url_for('dashboard'))

    dashboard_data = get_dashboard()
    students = Students.query.all()

    if request.method == 'POST':
        # check if the student is inside the class
        index_dates = Indexes.query.get(index_id).dates
        found = False
        for attendance in index_dates[0].attendance:
            if attendance.studentId == int(request.form['name']):
                found = True
                break

        if found:
            flash('Student is already enrolled into this class', 'warning')
            return redirect(url_for('view_class_students', index_id=index_id))
        else:
            # get the highest seat number
            seat_no = get_highest_seat_no(index_dates[0])
            for index_date in index_dates:
                new_attendance = Attendance(indexDateId=index_date.id, studentId=request.form['name'], seatNo=seat_no)
                db.session.add(new_attendance)
            db.session.commit()
            flash('Student has successfully enroll into this class', 'success')
            return redirect(url_for('view_class_students', index_id=index_id))

    return render_template('add_student_to_class.html', students=students, dashboard_data=dashboard_data)


@app.route('/edit_student_seat_no/<int:index_id>', methods=['GET', 'POST'])
@login_required
def edit_student_seat_no(index_id):
    if current_user.role != 'admin':
        flash('You are not authorized to perform this action', 'danger')
        return redirect(url_for('dashboard'))

    dashboard_data = get_dashboard()
    attendances = Indexes.query.get(index_id).dates[0].attendance
    course_code = attendances[0].indexDate.index.course.courseCode
    class_name = attendances[0].indexDate.index.className

    if request.method == "POST":
        index_dates = Indexes.query.get(index_id).dates
        for index_date in index_dates:
            for attendance in index_date.attendance:
                attendance.seatNo = request.form[f'seatNo_{attendance.studentId}']
            db.session.commit()
        flash('Successfully changed the seat number', 'success')
        return redirect(url_for('view_class_students', index_id=index_id))

    return render_template('edit_student_seat_no.html', course_code=course_code, class_name=class_name,
                           attendances=attendances, dashboard_data=dashboard_data)


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
    return redirect(url_for('view_class_dates', class_index=class_index.id))


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
    return redirect(url_for('view_class_dates', class_index=class_date.index.id))


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
