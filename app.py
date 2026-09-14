import os
from decimal import Decimal, InvalidOperation
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import CheckConstraint, UniqueConstraint, func, or_
from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash, check_password_hash


db = SQLAlchemy()

class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password = db.Column(db.String(255), nullable=False)
    phone = db.Column(db.String(40))
    university = db.Column(db.String(160))
    bookings = db.relationship('Booking', back_populates='student', cascade='all, delete-orphan')
    reviews = db.relationship('Review', back_populates='student', cascade='all, delete-orphan')

class SuperAdmin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)

class HostelAdmin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password = db.Column(db.String(255), nullable=False)
    phone = db.Column(db.String(40))
    hostels = db.relationship('Hostel', back_populates='owner', cascade='all, delete-orphan')

class Hostel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    hostel_admin_id = db.Column(db.Integer, db.ForeignKey('hostel_admin.id', ondelete='CASCADE'), nullable=False)
    name = db.Column(db.String(160), nullable=False)
    location = db.Column(db.String(255), nullable=False)
    price = db.Column(db.Numeric(12, 2), nullable=False)
    seats = db.Column(db.Integer, nullable=False)
    room_type = db.Column(db.String(80), nullable=False)
    distance_km = db.Column(db.Numeric(8, 2), nullable=False, default=0)
    description = db.Column(db.Text)
    image_url = db.Column(db.String(500))
    map_link = db.Column(db.String(500))
    listing_status = db.Column(db.String(20), nullable=False, default='inactive')
    payment_status = db.Column(db.String(20), nullable=False, default='unpaid')
    created_at = db.Column(db.DateTime, server_default=func.now(), nullable=False)
    owner = db.relationship('HostelAdmin', back_populates='hostels')
    bookings = db.relationship('Booking', back_populates='hostel', cascade='all, delete-orphan')
    reviews = db.relationship('Review', back_populates='hostel', cascade='all, delete-orphan')
    payments = db.relationship('Payment', back_populates='hostel', cascade='all, delete-orphan')
    __table_args__ = (CheckConstraint('price >= 0', name='ck_hostel_price'), CheckConstraint('seats >= 0', name='ck_hostel_seats'))

class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id', ondelete='CASCADE'), nullable=False)
    hostel_id = db.Column(db.Integer, db.ForeignKey('hostel.id', ondelete='CASCADE'), nullable=False)
    status = db.Column(db.String(20), nullable=False, default='pending')
    booking_date = db.Column(db.DateTime, server_default=func.now(), nullable=False)
    student = db.relationship('Student', back_populates='bookings')
    hostel = db.relationship('Hostel', back_populates='bookings')

class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    hostel_id = db.Column(db.Integer, db.ForeignKey('hostel.id', ondelete='CASCADE'), nullable=False)
    hostel_admin_id = db.Column(db.Integer, db.ForeignKey('hostel_admin.id', ondelete='CASCADE'), nullable=False)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    payment_method = db.Column(db.String(80), nullable=False)
    transaction_ref = db.Column(db.String(160))
    verification_status = db.Column(db.String(20), nullable=False, default='pending')
    payment_date = db.Column(db.DateTime, server_default=func.now(), nullable=False)
    hostel = db.relationship('Hostel', back_populates='payments')
    hostel_admin = db.relationship('HostelAdmin')

class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id', ondelete='CASCADE'), nullable=False)
    hostel_id = db.Column(db.Integer, db.ForeignKey('hostel.id', ondelete='CASCADE'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text)
    created_at = db.Column(db.DateTime, server_default=func.now(), nullable=False)
    student = db.relationship('Student', back_populates='reviews')
    hostel = db.relationship('Hostel', back_populates='reviews')
    __table_args__ = (CheckConstraint('rating BETWEEN 1 AND 5', name='ck_review_rating'), UniqueConstraint('student_id', 'hostel_id', name='uq_review_student_hostel'))


def role_required(role):
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if session.get('role') != role:
                flash('Please sign in to continue.', 'warning')
                return redirect(url_for({'student':'student_login','hostel_admin':'hostel_admin_login','admin':'admin_login'}[role]))
            return view(*args, **kwargs)
        return wrapped
    return decorator


def create_app():
    app = Flask(__name__)
    database_url = os.environ.get('DATABASE_URL', 'sqlite:///hostel_booking.db')
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql+psycopg://', 1)
    app.config.update(SECRET_KEY=os.environ.get('SECRET_KEY'), SQLALCHEMY_DATABASE_URI=database_url, SQLALCHEMY_TRACK_MODIFICATIONS=False)
    if not app.config['SECRET_KEY']:
        raise RuntimeError('SECRET_KEY environment variable is required')
    db.init_app(app)

    @app.cli.command('init-db')
    def init_db():
        with app.app_context():
            db.create_all()
            username = os.environ.get('ADMIN_USERNAME')
            password = os.environ.get('ADMIN_PASSWORD')
            if username and password and not SuperAdmin.query.filter_by(username=username).first():
                db.session.add(SuperAdmin(username=username, password=generate_password_hash(password)))
                db.session.commit()
        print('Database initialized. No demo data was created.')

    @app.route('/')
    def home():
        hostels = Hostel.query.filter_by(listing_status='active').order_by(Hostel.created_at.desc()).limit(6).all()
        return render_template('home.html', hostels=hostels)

    @app.route('/hostels')
    def hostels():
        q = request.args.get('q', '').strip()
        room_type = request.args.get('room_type', '').strip()
        query = Hostel.query.filter_by(listing_status='active')
        if q:
            query = query.filter(or_(Hostel.name.ilike(f'%{q}%'), Hostel.location.ilike(f'%{q}%')))
        if room_type:
            query = query.filter_by(room_type=room_type)
        return render_template('hostels.html', hostels=query.order_by(Hostel.created_at.desc()).all(), q=q, room_type=room_type)

    @app.route('/hostel/<int:hostel_id>')
    def hostel_detail(hostel_id):
        hostel = db.get_or_404(Hostel, hostel_id)
        if hostel.listing_status != 'active' and not (session.get('role') == 'admin' or session.get('user_id') == hostel.hostel_admin_id):
            flash('This hostel is not currently available.', 'warning')
            return redirect(url_for('hostels'))
        avg = db.session.query(func.avg(Review.rating)).filter_by(hostel_id=hostel.id).scalar() or 0
        return render_template('hostel_detail.html', hostel=hostel, avg_rating=round(float(avg), 1))

    @app.route('/student/register', methods=['GET','POST'])
    def student_register():
        if request.method == 'POST':
            email = request.form.get('email','').strip().lower(); password = request.form.get('password','').strip()
            if not request.form.get('name','').strip() or not email or len(password) < 8:
                flash('Name, email and a password of at least 8 characters are required.', 'danger')
            else:
                try:
                    db.session.add(Student(name=request.form['name'].strip(), email=email, password=generate_password_hash(password), phone=request.form.get('phone','').strip(), university=request.form.get('university','').strip()))
                    db.session.commit(); flash('Account created successfully.', 'success'); return redirect(url_for('student_login'))
                except IntegrityError:
                    db.session.rollback(); flash('An account with this email already exists.', 'danger')
        return render_template('auth.html', mode='student_register')

    @app.route('/student/login', methods=['GET','POST'])
    def student_login():
        if request.method == 'POST':
            user = Student.query.filter_by(email=request.form.get('email','').strip().lower()).first()
            if user and check_password_hash(user.password, request.form.get('password','')):
                session.clear(); session.update(user_id=user.id, role='student'); return redirect(url_for('home'))
            flash('Invalid email or password.', 'danger')
        return render_template('auth.html', mode='student_login')

    @app.route('/hostel-admin/register', methods=['GET','POST'])
    def hostel_admin_register():
        if request.method == 'POST':
            email = request.form.get('email','').strip().lower(); password = request.form.get('password','').strip()
            if not request.form.get('full_name','').strip() or not email or len(password) < 8:
                flash('Name, email and a password of at least 8 characters are required.', 'danger')
            else:
                try:
                    db.session.add(HostelAdmin(full_name=request.form['full_name'].strip(), email=email, password=generate_password_hash(password), phone=request.form.get('phone','').strip()))
                    db.session.commit(); flash('Owner account created successfully.', 'success'); return redirect(url_for('hostel_admin_login'))
                except IntegrityError:
                    db.session.rollback(); flash('An account with this email already exists.', 'danger')
        return render_template('auth.html', mode='hostel_admin_register')

    @app.route('/hostel-admin/login', methods=['GET','POST'])
    def hostel_admin_login():
        if request.method == 'POST':
            user = HostelAdmin.query.filter_by(email=request.form.get('email','').strip().lower()).first()
            if user and check_password_hash(user.password, request.form.get('password','')):
                session.clear(); session.update(user_id=user.id, role='hostel_admin'); return redirect(url_for('hostel_admin_dashboard'))
            flash('Invalid email or password.', 'danger')
        return render_template('auth.html', mode='hostel_admin_login')

    @app.route('/admin/login', methods=['GET','POST'])
    def admin_login():
        if request.method == 'POST':
            user = SuperAdmin.query.filter_by(username=request.form.get('username','').strip()).first()
            if user and check_password_hash(user.password, request.form.get('password','')):
                session.clear(); session.update(user_id=user.id, role='admin'); return redirect(url_for('admin_dashboard'))
            flash('Invalid administrator credentials.', 'danger')
        return render_template('auth.html', mode='admin_login')

    @app.route('/logout')
    def logout():
        session.clear(); return redirect(url_for('home'))

    @app.route('/booking/<int:hostel_id>', methods=['POST'])
    @role_required('student')
    def booking(hostel_id):
        hostel = db.get_or_404(Hostel, hostel_id)
        if hostel.listing_status != 'active' or hostel.seats <= 0:
            flash('This hostel is not available or has no seats.', 'danger'); return redirect(url_for('hostel_detail', hostel_id=hostel.id))
        existing = Booking.query.filter(Booking.student_id==session['user_id'], Booking.hostel_id==hostel.id, Booking.status.in_(['pending','approved'])).first()
        if existing:
            flash('You already have an active booking for this hostel.', 'warning'); return redirect(url_for('my_bookings'))
        hostel.seats -= 1
        db.session.add(Booking(student_id=session['user_id'], hostel_id=hostel.id)); db.session.commit()
        flash('Booking request submitted.', 'success'); return redirect(url_for('my_bookings'))

    @app.route('/my-bookings')
    @role_required('student')
    def my_bookings():
        return render_template('student_dashboard.html', bookings=Booking.query.filter_by(student_id=session['user_id']).order_by(Booking.booking_date.desc()).all())

    @app.route('/review/<int:hostel_id>', methods=['POST'])
    @role_required('student')
    def review(hostel_id):
        db.get_or_404(Hostel, hostel_id)
        try: rating = int(request.form.get('rating','0'))
        except ValueError: rating = 0
        if rating not in range(1,6):
            flash('Rating must be between 1 and 5.', 'danger')
        elif Review.query.filter_by(student_id=session['user_id'], hostel_id=hostel_id).first():
            flash('You have already reviewed this hostel.', 'warning')
        else:
            db.session.add(Review(student_id=session['user_id'], hostel_id=hostel_id, rating=rating, comment=request.form.get('comment','').strip())); db.session.commit(); flash('Review submitted.', 'success')
        return redirect(url_for('hostel_detail', hostel_id=hostel_id))

    @app.route('/hostel-admin/dashboard')
    @role_required('hostel_admin')
    def hostel_admin_dashboard():
        hostels = Hostel.query.filter_by(hostel_admin_id=session['user_id']).order_by(Hostel.created_at.desc()).all()
        bookings = Booking.query.join(Hostel).filter(Hostel.hostel_admin_id==session['user_id']).order_by(Booking.booking_date.desc()).all()
        return render_template('owner_dashboard.html', hostels=hostels, bookings=bookings)

    @app.route('/hostel-admin/add-hostel', methods=['GET','POST'])
    @role_required('hostel_admin')
    def add_hostel():
        if request.method == 'POST':
            try:
                price=Decimal(request.form.get('price','0')); seats=int(request.form.get('seats','0')); distance=Decimal(request.form.get('distance_km','0') or '0')
                if price < 0 or seats < 0 or distance < 0: raise ValueError
            except (InvalidOperation, ValueError):
                flash('Price, seats and distance must be valid non-negative values.', 'danger'); return render_template('hostel_form.html')
            required = ['name','location','room_type']
            if any(not request.form.get(x,'').strip() for x in required):
                flash('Name, location and room type are required.', 'danger'); return render_template('hostel_form.html')
            db.session.add(Hostel(hostel_admin_id=session['user_id'], name=request.form['name'].strip(), location=request.form['location'].strip(), price=price, seats=seats, room_type=request.form['room_type'].strip(), distance_km=distance, description=request.form.get('description','').strip(), image_url=request.form.get('image_url','').strip(), map_link=request.form.get('map_link','').strip()))
            db.session.commit(); flash('Hostel submitted for administrator approval.', 'success'); return redirect(url_for('hostel_admin_dashboard'))
        return render_template('hostel_form.html')

    @app.route('/hostel-admin/booking/<int:booking_id>/<action>', methods=['POST'])
    @role_required('hostel_admin')
    def owner_booking_action(booking_id, action):
        b=db.get_or_404(Booking, booking_id)
        if b.hostel.hostel_admin_id != session['user_id']: return redirect(url_for('hostel_admin_dashboard'))
        if action=='approve' and b.status=='pending': b.status='approved'
        elif action=='reject' and b.status in ('pending','approved'): b.status='rejected'; b.hostel.seats += 1
        else: flash('Invalid booking action.', 'warning'); return redirect(url_for('hostel_admin_dashboard'))
        db.session.commit(); flash('Booking updated.', 'success'); return redirect(url_for('hostel_admin_dashboard'))

    @app.route('/hostel-admin/payment/<int:hostel_id>', methods=['POST'])
    @role_required('hostel_admin')
    def payment(hostel_id):
        hostel=Hostel.query.filter_by(id=hostel_id, hostel_admin_id=session['user_id']).first_or_404()
        try: amount=Decimal(request.form.get('amount','0'))
        except InvalidOperation: amount=Decimal('0')
        if amount <= 0 or not request.form.get('payment_method','').strip():
            flash('A valid amount and payment method are required.', 'danger')
        else:
            db.session.add(Payment(hostel_id=hostel.id, hostel_admin_id=session['user_id'], amount=amount, payment_method=request.form['payment_method'].strip(), transaction_ref=request.form.get('transaction_ref','').strip())); db.session.commit(); flash('Payment submitted for verification.', 'success')
        return redirect(url_for('hostel_admin_dashboard'))

    @app.route('/admin/dashboard')
    @role_required('admin')
    def admin_dashboard():
        return render_template('admin_dashboard.html', students=Student.query.count(), hostels=Hostel.query.count(), bookings=Booking.query.count(), pending_payments=Payment.query.filter_by(verification_status='pending').count(), pending_hostels=Hostel.query.filter_by(listing_status='inactive').count())

    @app.route('/admin/manage-bookings')
    @role_required('admin')
    def manage_bookings():
        return render_template('admin_bookings.html', bookings=Booking.query.order_by(Booking.booking_date.desc()).all())

    @app.route('/admin/manage-payments')
    @role_required('admin')
    def manage_payments():
        return render_template('admin_payments.html', payments=Payment.query.order_by(Payment.payment_date.desc()).all())

    @app.route('/admin/payment/<int:payment_id>/<action>', methods=['POST'])
    @role_required('admin')
    def payment_action(payment_id, action):
        p=db.get_or_404(Payment,payment_id)
        if action=='approve': p.verification_status='approved'; p.hostel.payment_status='paid'; p.hostel.listing_status='active'
        elif action=='reject': p.verification_status='rejected'
        else: flash('Invalid payment action.','warning'); return redirect(url_for('manage_payments'))
        db.session.commit(); flash('Payment status updated.','success'); return redirect(url_for('manage_payments'))

    @app.route('/admin/hostel/<int:hostel_id>/<action>', methods=['POST'])
    @role_required('admin')
    def hostel_action(hostel_id, action):
        h=db.get_or_404(Hostel,hostel_id)
        if action=='approve': h.listing_status='active'
        elif action=='disable': h.listing_status='inactive'
        else: flash('Invalid listing action.','warning'); return redirect(url_for('admin_dashboard'))
        db.session.commit(); flash('Hostel listing updated.','success'); return redirect(url_for('admin_dashboard'))

    return app

app = create_app()

if __name__ == '__main__':
    app.run(debug=False)
