from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, login_required, logout_user, current_user
from .models import User
from . import db
import logging

auth = Blueprint('auth', __name__)

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        # Log detailed login attempt information
        current_app.logger.info(f"Login attempt for email: {email}")
        
        try:
            # Check if user exists
            user = User.query.filter_by(email=email).first()
            
            # Log user query result
            if user:
                current_app.logger.info(f"User found: {user.email}, ID: {user.id}, Role: {user.role}")
                current_app.logger.info(f"Stored password hash: {user.password}")
            else:
                current_app.logger.warning(f"No user found with email: {email}")
            
            # Detailed password verification logging
            if user:
                password_match = check_password_hash(user.password, password)
                current_app.logger.info(f"Password match result: {password_match}")
                
                if password_match:
                    # Check if user is active
                    if not user.is_active:
                        current_app.logger.warning(f"Inactive user login attempt: {email}")
                        flash('Your account is not active. Please contact an administrator.', 'error')
                        return render_template('login.html')
                    
                    # Login user based on role
                    login_user(user, remember=True)
                    
                    # Redirect based on role
                    if user.role == 'agency':
                        flash('Logged in as Agency successfully.', 'success')
                        return redirect(url_for('main.home'))
                    elif user.role in ['secretary', 'manager', 'admin', 'employee']:
                        flash(f'Logged in as {user.role.capitalize()} successfully.', 'success')
                        return redirect(url_for('main.dashboard'))
                    else:
                        current_app.logger.warning(f"Invalid user role: {user.role}")
                        flash('Invalid user role.', 'error')
                        return render_template('login.html')
                else:
                    current_app.logger.warning(f"Password mismatch for user: {email}")
            
            # If no matching user found or password incorrect
            current_app.logger.error(f"Login failed for email: {email}")
            flash('Invalid email or password. Please try again.', 'error')
        
        except Exception as e:
            # Log any unexpected errors
            current_app.logger.error(f"Unexpected error during login: {str(e)}")
            flash('An unexpected error occurred. Please try again.', 'error')
    
    return render_template('login.html')

@auth.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        name = request.form.get('name')
        password = request.form.get('password')
        employee_id = request.form.get('employee_id')
        
        if User.query.filter_by(email=email).first():
            flash('Email already exists.', 'error')
        elif User.query.filter_by(employee_id=employee_id).first():
            flash('Employee ID already exists.', 'error')
        else:
            # Make the first user an admin
            is_admin = User.query.first() is None
            new_user = User(
                email=email,
                name=name,
                password=generate_password_hash(password, method='pbkdf2:sha256'),
                employee_id=employee_id,
                is_admin=is_admin
            )
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user, remember=True)
            if is_admin:
                flash('Admin account created successfully!', 'success')
            else:
                flash('Employee account created successfully!', 'success')
            return redirect(url_for('main.dashboard'))
    
    return render_template('register.html')

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))
