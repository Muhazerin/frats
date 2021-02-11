from models import app, db, Users, Staffs, Students
from flask import url_for, render_template, redirect, request, flash
from forms import LoginForm, RegistrationForm
from flask_login import login_user, current_user, login_required, logout_user
from flask_bcrypt import check_password_hash, generate_password_hash
import values


def get_dashboard():
    dashboard_data = values.dashboards['admin'] if current_user.type == 'admin' else \
                    values.dashboards['staff'] if current_user.type == 'staff' else \
                    values.dashboards['student']
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
    if current_user.type != 'admin':
        flash('You are not authorized to perform this action', 'danger')
        return redirect(url_for('dashboard'))

    dashboard_data = get_dashboard()
    form = RegistrationForm()

    if form.validate_on_submit():
        appointment = 'student' if form.appointment.data == 'Student' else 'staff'
        hashed_password = generate_password_hash(form.password.data).decode('utf-8')
        user = Users(email=form.email.data.casefold(), password=hashed_password, type=appointment)
        db.session.add(user)
        db.session.commit()
        if appointment == 'student':
            person = Students(name=form.name.data, matricNo=form.personNo.data, userId=user.id)
        else:
            person = Staffs(name=form.name.data, employeeNo=form.personNo.data,
                            role=form.appointment.data.casefold(), userId=user.id)
        db.session.add(person)
        db.session.commit()

        if appointment == 'student':
            flash('A student account has been created', 'success')
        else:
            flash('A staff account has been created', 'success')
        return redirect(url_for('dashboard'))
    return render_template('register_account.html', form=form, title='Register', dashboard_data=dashboard_data)


@app.route('/dashboard')
@login_required
def dashboard():
    dashboard_data = get_dashboard()
    return render_template('dashboard.html', dashboard_data=dashboard_data, title="Dashboard")


if __name__ == '__main__':
    app.run(debug=True)
