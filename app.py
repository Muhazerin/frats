from flask import url_for, render_template, redirect, request, flash
from flask_bcrypt import check_password_hash, generate_password_hash
from flask_login import login_user, current_user, login_required, logout_user

import csv
import values
import datetime
from forms import LoginForm, RegistrationForm, AdminAddFileForm
from models import app, db, Users, Staffs, Students, Courses, Indexes, StaffInCharged, IndexDates, Attendance


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
                    student = Students(name=student_details['name'], matricNo=student_details['matricNo'])
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
                    flash(f'Student {class_details["matricNo"]} is not inside the database. Please add this student first',
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

    dashboard_data = get_dashboard()
    attendances = Attendance.query.filter_by(indexDateId=class_date_id).all()

    return render_template('view_attendance.html', dashboard_data=dashboard_data, attendances=attendances,
                           date=attendances[0].indexDate.date, class_name=attendances[0].indexDate.index.className)




if __name__ == '__main__':
    app.run(debug=True)
