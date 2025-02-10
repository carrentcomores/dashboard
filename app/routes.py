from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify, current_app
from flask_login import login_required, current_user
from .models import Car, Booking, Customer, CarImage, Maintenance, Expense, Income, User, AgencyVisibleCar, AgencyCarStatus
from . import db
from datetime import datetime
import os
from werkzeug.utils import secure_filename
import json
from datetime import timedelta
from werkzeug.security import generate_password_hash
from functools import wraps
from sqlalchemy import extract
from sqlalchemy.orm import joinedload
from flask import send_from_directory
from sqlalchemy.exc import SQLAlchemyError, DatabaseError

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('You do not have permission to access this page.', 'danger')
            return redirect(url_for('main.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def manager_or_admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or (not current_user.is_admin and current_user.role != 'manager'):
            flash('You do not have permission to access this page.', 'danger')
            return redirect(url_for('main.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def secretary_or_admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or (not current_user.is_admin and current_user.role != 'secretary'):
            flash('You do not have permission to access this page.', 'danger')
            return redirect(url_for('main.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def agency_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('auth.login'))
        
        # Check if the current user is an agency
        if current_user.role == 'agency':
            flash('You do not have permission to access this page.', 'error')
            return redirect(url_for('main.home'))
        
        return f(*args, **kwargs)
    return decorated_function

main = Blueprint('main', __name__)

# Configure upload folder
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'app', 'static', 'uploads', 'cars')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_image(file, car_id):
    if file and allowed_file(file.filename):
        # Create car directory if it doesn't exist
        car_dir = os.path.join(UPLOAD_FOLDER, str(car_id))
        os.makedirs(car_dir, exist_ok=True)
        
        # Secure the filename and save the file
        filename = secure_filename(file.filename)
        file_path = os.path.join(car_dir, filename)
        file.save(file_path)
        
        # Return the relative path for database storage
        return os.path.join('uploads', 'cars', str(car_id), filename)
    return None

@main.route('/')
@login_required
def home():
    # Check if the current user is an agency
    if current_user.role == 'agency':
        # Get the IDs of cars visible to this agency
        visible_car_ids = [vc.car_id for vc in current_user.agency_visible_cars]
        
        # Filter cars based on visibility and sort by display_order
        cars = Car.query.filter(Car.id.in_(visible_car_ids)).order_by(Car.display_order).all()
    else:
        # For non-agency users, show all cars sorted by display_order
        cars = Car.query.order_by(Car.display_order).all()

    # Get active bookings with their associated cars and customers
    active_bookings = Booking.query.join(Customer).join(User, Booking.employee_id == User.id).filter(
        Booking.status == 'active',
        User.role.in_(['admin', 'manager'])
    ).options(
        joinedload(Booking.car),
        joinedload(Booking.customer),
        joinedload(Booking.employee)
    ).all()

    # Create a dictionary to store booking information for each car
    car_bookings = {}
    for booking in active_bookings:
        car_bookings[booking.car_id] = {
            'customer_name': booking.customer.name,
            'start_date': booking.start_date,
            'end_date': booking.end_date,
            'booked_by_role': booking.employee.role
        }

    # Get agency car statuses that override default availability
    agency_car_statuses = AgencyCarStatus.query.filter(
        AgencyCarStatus.status.in_(['booked', 'unavailable'])
    ).all()

    # Create a dictionary to store agency-specific car statuses
    agency_statuses = {}
    for status in agency_car_statuses:
        agency_statuses[status.car_id] = status.status

    # Annotate cars with their booking and agency status information
    for car in cars:
        car.current_booking = car_bookings.get(car.id)
        
        # Override car availability based on booking and agency status
        if car.current_booking:
            # If booked by admin/manager, prevent agency status modification
            if car.current_booking['booked_by_role'] in ['admin', 'manager']:
                car.is_available = False
        elif car.id in agency_statuses:
            # Agency-specific status for non-booked cars
            if agency_statuses[car.id] == 'booked':
                car.current_booking = {'customer_name': 'Agency Marked', 'start_date': datetime.now(), 'end_date': datetime.now()}
            elif agency_statuses[car.id] == 'unavailable':
                car.is_available = False

    return render_template('home.html', 
                           cars=cars, 
                           total_cars=len(cars), 
                           booked_cars_count=len(active_bookings))

@main.route('/dashboard')
@login_required
@agency_only
def dashboard():
    # Get current month and year
    current_month = datetime.now().month
    current_year = datetime.now().year

    # Income Summary
    incomes = Income.query.filter(
        extract('year', Income.date) == current_year,
        extract('month', Income.date) == current_month
    ).all()
    total_income = sum(income.amount for income in incomes)
    income_by_category = {}
    for income in incomes:
        income_by_category[income.category] = income_by_category.get(income.category, 0) + income.amount

    # Expense Summary
    expenses = Expense.query.filter(
        extract('year', Expense.date) == current_year,
        extract('month', Expense.date) == current_month
    ).all()
    total_expenses = sum(expense.amount for expense in expenses)
    expense_by_category = {}
    for expense in expenses:
        expense_by_category[expense.category] = expense_by_category.get(expense.category, 0) + expense.amount

    # Booking Summary
    total_bookings = Booking.query.filter(
        extract('year', Booking.start_date) == current_year,
        extract('month', Booking.start_date) == current_month
    ).count()

    # Car Availability
    total_cars = Car.query.count()
    available_cars = Car.query.filter_by(is_available=True).count()

    # Prepare context for dashboard
    dashboard_context = {
        'total_income': total_income,
        'income_by_category': income_by_category,
        'total_expenses': total_expenses,
        'expense_by_category': expense_by_category,
        'total_bookings': total_bookings,
        'total_cars': total_cars,
        'available_cars': available_cars,
        'current_month': datetime.now().strftime('%B'),
        'current_year': current_year,
        'current_datetime': datetime.now()
    }

    # If not admin or manager/secretary, show only user's bookings
    if not (current_user.is_admin or current_user.role in ['manager', 'secretary']):
        dashboard_context['bookings'] = Booking.query.filter_by(employee_id=current_user.id).order_by(Booking.created_at.desc()).all()
    else:
        dashboard_context['bookings'] = Booking.query.order_by(Booking.created_at.desc()).all()
        dashboard_context['cars'] = Car.query.all()

    return render_template('dashboard.html', **dashboard_context)

@main.route('/car/<int:car_id>')
def car_details(car_id):
    car = Car.query.get_or_404(car_id)
    return render_template('car_details.html', car=car)

@main.route('/book/<int:car_id>', methods=['GET', 'POST'])
@login_required
def book_car(car_id):
    # Check user role - only admin and secretary can book cars
    if current_user.role not in ['admin', 'secretary']:
        flash('You do not have permission to book cars. Only admins and secretaries can book cars.', 'error')
        return redirect(url_for('main.home'))
    
    car = Car.query.get_or_404(car_id)
    
    if not car.is_available:
        flash('This car is currently rented and not available for booking.', 'error')
        return redirect(url_for('main.home'))
    
    if request.method == 'POST':
        try:
            # Detailed logging of form data
            print("Booking Form Data:")
            for key, value in request.form.items():
                print(f"{key}: {value}")
            
            # Comprehensive field validation
            required_fields = [
                'customer_name', 'customer_phone', 'license_number', 
                'nin_passport_number', 'nationality', 'start_date', 'end_date'
            ]
            
            # Check for missing fields
            missing_fields = [field for field in required_fields if not request.form.get(field)]
            if missing_fields:
                error_msg = f"Missing required fields: {', '.join(missing_fields)}"
                print(error_msg)
                flash(error_msg, 'error')
                return render_template('book_car.html', car=car)
            
            # Extract customer details with default empty string
            name = request.form.get('customer_name', '').strip()
            phone = request.form.get('customer_phone', '').strip()
            email = request.form.get('customer_email', '').strip()
            address = request.form.get('customer_address', '').strip()
            license_number = request.form.get('license_number', '').strip()
            nin_passport_number = request.form.get('nin_passport_number', '').strip()
            nationality = request.form.get('nationality', '').strip()
            
            # Validate key fields
            if not name or not phone or not nin_passport_number:
                flash('Name, Phone, and NIN/Passport Number are required.', 'error')
                return render_template('book_car.html', car=car)
            
            # Check for existing customer
            existing_customer = Customer.query.filter_by(nin_passport_number=nin_passport_number).first()
            
            # Determine customer (existing or new)
            if existing_customer:
                # Update existing customer details
                existing_customer.name = name
                existing_customer.phone = phone
                existing_customer.email = email
                existing_customer.address = address
                existing_customer.license_number = license_number
                existing_customer.nationality = nationality
                customer = existing_customer
                print(f"Updating existing customer: {customer.id}")
            else:
                # Create new customer
                customer = Customer(
                    name=name,
                    phone=phone,
                    email=email,
                    address=address,
                    license_number=license_number,
                    nin_passport_number=nin_passport_number,
                    nationality=nationality,
                    created_at=datetime.now()
                )
                db.session.add(customer)
                
                # Flush to get the customer ID
                try:
                    db.session.flush()
                    print(f"New customer created with ID: {customer.id}")
                except Exception as customer_save_error:
                    print(f"Error saving customer: {customer_save_error}")
                    db.session.rollback()
                    flash('Error creating customer.', 'error')
                    return render_template('book_car.html', car=car)
            
            # Validate customer has an ID
            if not customer.id:
                print("Customer ID is None")
                flash('Error: Could not create or retrieve customer.', 'error')
                return render_template('book_car.html', car=car)
            
            # Parse and validate dates
            try:
                start_date = datetime.strptime(request.form.get('start_date'), '%Y-%m-%d')
                end_date = datetime.strptime(request.form.get('end_date'), '%Y-%m-%d')
                
                if start_date >= end_date:
                    flash('End date must be after start date.', 'error')
                    return render_template('book_car.html', car=car)
            except ValueError:
                flash('Invalid date format. Please use YYYY-MM-DD', 'error')
                return render_template('book_car.html', car=car)
            
            # Calculate total cost and deposit
            days = (end_date - start_date).days + 1
            total_cost = car.daily_rate * days
            deposit_amount = total_cost * 0.3  # 30% deposit
            
            # Find all admin agencies
            admin_agencies = User.query.filter_by(role='admin').all()
            
            if not admin_agencies:
                flash('No admin agencies found. Cannot complete booking.', 'error')
                return redirect(url_for('main.home'))
            
            # Determine the booking source
            if current_user.is_admin:
                booking_source_id = current_user.id
                booking_source_type = "Admin"
            else:
                booking_source_id = admin_agencies[0].id
                booking_source_type = "Secretary"
            
            # Update car status with specific 'booked' status
            car.is_available = False
            
            # Create or update AgencyCarStatus for all admin agencies
            for admin_agency in admin_agencies:
                # Update or create AgencyCarStatus
                agency_car_status = AgencyCarStatus.query.filter_by(
                    agency_id=admin_agency.id, 
                    car_id=car.id
                ).first()
                
                if agency_car_status:
                    agency_car_status.status = 'booked'
                else:
                    agency_car_status = AgencyCarStatus(
                        agency_id=admin_agency.id, 
                        car_id=car.id, 
                        status='booked'
                    )
                    db.session.add(agency_car_status)
                
                # Create or update AgencyVisibleCar
                agency_visible_car = AgencyVisibleCar.query.filter_by(
                    agency_id=admin_agency.id, 
                    car_id=car.id
                ).first()
                
                if not agency_visible_car:
                    agency_visible_car = AgencyVisibleCar(
                        agency_id=admin_agency.id, 
                        car_id=car.id
                    )
                    db.session.add(agency_visible_car)
            
            # Create booking record 
            new_booking = Booking(
                employee_id=booking_source_id,
                customer_id=customer.id,
                car_id=car.id,
                start_date=datetime.strptime(request.form.get('start_date'), '%Y-%m-%d'),
                end_date=datetime.strptime(request.form.get('end_date'), '%Y-%m-%d'),
                total_cost=total_cost,
                deposit_amount=deposit_amount,
                status='active',
                notes=f"Booked through {booking_source_type} {current_user.name}"
            )
            db.session.add(new_booking)
            
            # Commit transaction
            db.session.commit()
            
            # Flash success message
            if not existing_customer:
                flash('New customer created and booking completed successfully!', 'success')
            else:
                flash('Booking completed successfully!', 'success')
            
            return redirect(url_for('main.dashboard'))
        
        except Exception as e:
            # Rollback transaction and log error
            db.session.rollback()
            print(f"Booking Error: {str(e)}")
            import traceback
            traceback.print_exc()
            
            flash(f'Error creating booking: {str(e)}', 'error')
            return render_template('book_car.html', car=car)
    
    return render_template('book_car.html', car=car)

@main.route('/search_customer')
@login_required
def search_customer():
    query = request.args.get('query', '')
    
    # Search across multiple fields
    customers = Customer.query.filter(
        (Customer.phone.contains(query)) |
        (Customer.name.contains(query)) |
        (Customer.license_number.contains(query)) |
        (Customer.nin_passport_number.contains(query))
    ).all()
    
    return jsonify([{
        'id': c.id,
        'name': c.name,
        'phone': c.phone,
        'email': c.email,
        'address': c.address,
        'license_number': c.license_number,
        'nin_passport_number': c.nin_passport_number,
        'nationality': c.nationality
    } for c in customers])

@main.route('/customer_history/<int:customer_id>')
@login_required
def customer_history(customer_id):
    customer = Customer.query.get_or_404(customer_id)
    bookings = Booking.query.filter_by(customer_id=customer_id).order_by(Booking.created_at.desc()).all()
    return render_template('customer_history.html', customer=customer, bookings=bookings)

@main.route('/manage_cars', methods=['GET', 'POST'])
@login_required
@manager_or_admin_required
def manage_cars():
    if request.method == 'POST':
        # Existing car addition logic
        model = request.form.get('model')
        year = request.form.get('year')
        license_plate = request.form.get('license_plate')
        daily_rate = request.form.get('daily_rate')
        category = request.form.get('category')
        description = request.form.get('description')
        features = request.form.get('features')

        # Check if car with same license plate already exists
        existing_car = Car.query.filter_by(license_plate=license_plate).first()
        if existing_car:
            flash('A car with this license plate already exists.', 'danger')
            return redirect(url_for('main.manage_cars'))

        # Create new car
        new_car = Car(
            model=model,
            year=year,
            license_plate=license_plate,
            daily_rate=daily_rate,
            category=category,
            description=description,
            features=features
        )
        
        # Set display order to the next available order
        max_order = db.session.query(db.func.max(Car.display_order)).scalar() or 0
        new_car.display_order = max_order + 1

        # Handle image upload
        images = request.files.getlist('images')
        db.session.add(new_car)
        db.session.flush()  # To get the new car's ID

        # Save car images
        for image in images:
            if image and allowed_file(image.filename):
                filename = save_image(image, new_car.id)
                if filename:
                    car_image = CarImage(car_id=new_car.id, image_path=filename)
                    db.session.add(car_image)

                    # Set first image as main image if not already set
                    if not new_car.main_image:
                        new_car.main_image = filename

        try:
            db.session.commit()
            flash('Car added successfully!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding car: {str(e)}', 'danger')

        return redirect(url_for('main.manage_cars'))

    # Fetch cars, ordered by display_order
    cars = Car.query.order_by(Car.display_order).all()

    # Ensure all cars have a display_order
    for index, car in enumerate(cars, start=1):
        if car.display_order == 0:
            car.display_order = index
    
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        flash(f'Error setting display order: {str(e)}', 'danger')

    return render_template('manage_cars.html', cars=cars)

@main.route('/manage_cars/upload_images/<int:car_id>', methods=['POST'])
@login_required
def upload_car_images(car_id):
    # Allow both admin and manager to upload car images
    if not (current_user.is_admin or current_user.role == 'manager'):
        return jsonify({'error': 'Access denied'}), 403
    
    car = Car.query.get_or_404(car_id)
    images = request.files.getlist('images')
    
    try:
        for image in images:
            if image and allowed_file(image.filename):
                image_path = save_image(image, car.id)
                if image_path:
                    car_image = CarImage(
                        car_id=car.id,
                        image_path=image_path,
                        caption=request.form.get('caption')
                    )
                    db.session.add(car_image)
                    
                    # Set as main image if car doesn't have one
                    if not car.main_image:
                        car.main_image = image_path
        
        db.session.commit()
        return jsonify({'message': 'Images uploaded successfully'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Error uploading images'}), 500

@main.route('/manage_cars/delete_image/<int:image_id>', methods=['DELETE'])
@login_required
def delete_car_image(image_id):
    # Log the incoming request details
    current_app.logger.info(f"Delete car image request received. Image ID: {image_id}")
    current_app.logger.info(f"Current User: {current_user.email}, Is Admin: {current_user.is_admin}, Role: {current_user.role}")
    
    # Allow both admin and manager to delete car images
    if not (current_user.is_admin or current_user.role == 'manager'):
        current_app.logger.warning(f"Unauthorized delete image attempt by user {current_user.email}")
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        # Try to find the image
        image = CarImage.query.get(image_id)
        if not image:
            current_app.logger.error(f"Image not found. Image ID: {image_id}")
            return jsonify({'error': 'Image not found'}), 404
        
        car = image.car  # Store reference to car before deleting image
        
        # Delete the physical file
        file_path = os.path.join(current_app.root_path, 'static', image.image_path)
        current_app.logger.info(f"Attempting to delete file: {file_path}")
        
        if os.path.exists(file_path):
            os.remove(file_path)
            current_app.logger.info(f"File deleted successfully: {file_path}")
        else:
            current_app.logger.warning(f"File does not exist: {file_path}")
        
        # If this was the main image, set another image as main
        if image.is_main:
            next_image = CarImage.query.filter_by(car_id=image.car_id).filter(CarImage.id != image_id).first()
            if next_image:
                next_image.is_main = True
                car.main_image = next_image.image_path
                current_app.logger.info(f"New main image set: {next_image.image_path}")
            else:
                car.main_image = None
                current_app.logger.info("No alternative main image found")
        
        # Delete the image record
        db.session.delete(image)
        db.session.commit()
        
        current_app.logger.info(f"Image {image_id} deleted successfully")
        return jsonify({'message': 'Image deleted successfully', 'car_id': car.id}), 200
        
    except Exception as e:
        # Log the full error for server-side debugging
        current_app.logger.error(f"Error deleting car image: {str(e)}", exc_info=True)
        
        # Rollback the session to prevent any partial commits
        db.session.rollback()
        
        # Return a JSON error response with a generic message
        return jsonify({
            'error': 'Failed to delete image',
            'details': str(e)
        }), 500

@main.route('/manage_cars/edit/<int:car_id>', methods=['POST'])
@login_required
def edit_car(car_id):
    # Allow both admin and manager to edit cars
    if not (current_user.is_admin or current_user.role == 'manager'):
        return jsonify({'error': 'Access denied'}), 403
    
    car = Car.query.get_or_404(car_id)
    
    try:
        # Log all incoming form data for debugging
        current_app.logger.info(f"Editing car {car_id}: Received form data: {dict(request.form)}")
        
        # Validate daily rate is a whole number
        try:
            daily_rate = int(request.form.get('daily_rate', 0))
            if daily_rate <= 0:
                return jsonify({'error': 'Daily rate must be a positive whole number.'}), 400
        except ValueError:
            return jsonify({'error': 'Invalid daily rate. Please enter a whole number.'}), 400
        
        # Explicitly handle each field
        car.model = request.form.get('model', car.model)
        car.year = int(request.form.get('year', car.year))
        car.license_plate = request.form.get('license_plate', car.license_plate)
        car.daily_rate = daily_rate
        car.category = request.form.get('category', car.category)
        
        # Explicitly handle is_available as a string
        is_available_str = request.form.get('is_available', 'false').lower()
        car.is_available = is_available_str in ['true', '1', 'yes']
        
        # Handle optional fields with default values
        car.description = request.form.get('description', car.description or '')
        car.features = request.form.get('features', car.features or '')
        
        db.session.commit()
        
        # Log successful update
        current_app.logger.info(f"Successfully updated car {car_id}")
        
        return jsonify({
            'message': 'Car updated successfully', 
            'car': {
                'model': car.model,
                'year': car.year,
                'license_plate': car.license_plate,
                'daily_rate': car.daily_rate,
                'category': car.category,
                'is_available': car.is_available,
                'description': car.description,
                'features': car.features
            }
        })
    except Exception as e:
        # Log the full error for debugging
        current_app.logger.error(f"Error updating car {car_id}: {str(e)}", exc_info=True)
        db.session.rollback()
        return jsonify({'error': f'Error updating car: {str(e)}'}), 500

@main.route('/manage_cars/delete/<int:car_id>', methods=['POST'])
@login_required
def delete_car(car_id):
    # Allow both admin and manager to delete cars
    if not (current_user.is_admin or current_user.role == 'manager'):
        return jsonify({'error': 'Access denied'}), 403
    
    car = Car.query.get_or_404(car_id)
    
    try:
        db.session.delete(car)
        db.session.commit()
        return jsonify({'message': 'Car deleted successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Error deleting car'}), 500

@main.route('/manage_cars/get_images/<int:car_id>', methods=['GET'])
@login_required
def get_car_images(car_id):
    car = Car.query.get_or_404(car_id)
    images = []
    
    for image in car.images:
        images.append({
            'id': image.id,
            'path': url_for('static', filename=image.image_path),
            'caption': image.caption,
            'is_main': image.is_main
        })
    
    return jsonify(images)

@main.route('/manage_cars/set_main_image/<int:image_id>', methods=['POST'])
@login_required
def set_main_image(image_id):
    # Allow both admin and manager to set main image
    if not (current_user.is_admin or current_user.role == 'manager'):
        return jsonify({'error': 'Access denied'}), 403
    
    image = CarImage.query.get_or_404(image_id)
    car = image.car
    
    # Remove main flag from all images
    for img in car.images:
        img.is_main = False
    
    # Set new main image
    image.is_main = True
    car.main_image = image.image_path
    
    try:
        db.session.commit()
        return jsonify({'message': 'Main image updated successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Error updating main image'}), 500

@main.route('/update_return_date', methods=['POST'])
@login_required
def update_return_date():
    try:
        booking_id = request.form.get('booking_id')
        new_end_date = datetime.strptime(request.form.get('new_end_date'), '%Y-%m-%d')
        
        booking = Booking.query.get_or_404(booking_id)
        
        # Determine the booking source from the notes
        booking_source = None
        if booking.notes:
            if "Booked through Secretary" in booking.notes:
                booking_source = "Secretary"
            elif "Booked through Admin" in booking.notes:
                booking_source = "Admin"
        
        # Permission check
        if current_user.is_admin:
            # Admins can edit any booking
            pass
        elif current_user.role == 'secretary':
            # Secretaries can edit any booking, but log the action
            current_app.logger.info(
                f"Secretary {current_user.id} editing booking {booking_id} "
                f"originally booked through {booking_source}"
            )
        else:
            # Other roles can only edit their own bookings
            if booking.employee_id != current_user.id:
                return jsonify({
                    'success': False, 
                    'error': 'You are not authorized to edit this booking.'
                }), 403
            
        # Validate the new end date
        if new_end_date <= booking.start_date:
            return jsonify({
                'success': False, 
                'error': 'End date must be after start date'
            }), 400
            
        # Calculate new total cost
        days = (new_end_date - booking.start_date).days
        total_cost = days * booking.car.daily_rate
        
        # Update booking
        booking.end_date = new_end_date
        booking.total_cost = total_cost
        
        # If edited by a secretary, update the notes to reflect this
        if current_user.role == 'secretary':
            booking.notes += f" (Edited by Secretary {current_user.name} on {datetime.now().strftime('%Y-%m-%d %H:%M')})"
        
        db.session.commit()
        
        # Log the booking update
        current_app.logger.info(
            f"Booking {booking_id} updated: "
            f"New end date: {new_end_date}, "
            f"New total cost: {total_cost}, "
            f"Updated by: {current_user.name} ({current_user.role})"
        )
        
        return jsonify({'success': True})
        
    except ValueError:
        return jsonify({
            'success': False, 
            'error': 'Invalid date format'
        }), 400
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating return date: {str(e)}", exc_info=True)
        return jsonify({
            'success': False, 
            'error': str(e)
        }), 500

@main.route('/delete_booking/<int:booking_id>', methods=['POST'])
@login_required
def delete_booking(booking_id):
    # Import additional debugging tools
    import traceback
    
    # Detailed logging of the deletion attempt
    current_app.logger.info(f"Attempting to delete booking {booking_id}")
    current_app.logger.info(f"Current user: {current_user.id}, Name: {current_user.name}, Role: {current_user.role}")
    
    try:
        # Find the booking with comprehensive error checking
        booking = Booking.query.get(booking_id)
        if not booking:
            current_app.logger.error(f"Booking with ID {booking_id} not found in database")
            return jsonify({
                'success': False, 
                'error': 'Booking not found.'
            }), 404
        
        # Log detailed booking information
        current_app.logger.info(f"Booking details - ID: {booking.id}, Car ID: {booking.car_id}, "
                                f"Customer ID: {booking.customer_id}, Employee ID: {booking.employee_id}, "
                                f"Status: {booking.status}")
        
        # Determine the booking source from the notes
        booking_source = None
        if booking.notes:
            if "Booked through Secretary" in booking.notes:
                booking_source = "Secretary"
            elif "Booked through Admin" in booking.notes:
                booking_source = "Admin"
        
        # Permission check
        if current_user.is_admin:
            # Admins can delete any booking
            pass
        elif current_user.role == 'secretary':
            # Secretaries can only delete bookings made by a secretary
            if booking_source != "Secretary":
                current_app.logger.warning(
                    f"Unauthorized deletion attempt for booking {booking_id}. "
                    f"Secretary {current_user.id} cannot delete a non-secretary booking."
                )
                return jsonify({
                    'success': False, 
                    'error': 'You can only delete bookings made by a secretary.'
                }), 403
        else:
            # Other roles cannot delete bookings
            current_app.logger.warning(
                f"Unauthorized deletion attempt for booking {booking_id}. "
                f"User {current_user.id} is not authorized to delete bookings."
            )
            return jsonify({
                'success': False, 
                'error': 'You are not authorized to delete bookings.'
            }), 403
        
        # Find the car associated with the booking
        car = Car.query.get(booking.car_id)
        if not car:
            current_app.logger.error(f"Car not found for booking {booking_id}")
            return jsonify({
                'success': False, 
                'error': 'Associated car not found.'
            }), 404
        
        # Log car details before deletion
        current_app.logger.info(f"Car details before deletion - ID: {car.id}, "
                                f"License Plate: {car.license_plate}, "
                                f"Current Availability: {car.is_available}")
        
        # Reset car availability completely
        car.is_available = True
        
        # Remove all agency-specific car status and visibility entries
        try:
            agency_car_status_query = AgencyCarStatus.query.filter_by(car_id=car.id)
            agency_car_status_count = agency_car_status_query.count()
            agency_car_status_query.delete()
            
            agency_visible_car_query = AgencyVisibleCar.query.filter_by(car_id=car.id)
            agency_visible_car_count = agency_visible_car_query.count()
            agency_visible_car_query.delete()
        except Exception as agency_delete_error:
            current_app.logger.error(f"Error removing agency entries: {str(agency_delete_error)}")
            current_app.logger.error(traceback.format_exc())
            return jsonify({
                'success': False, 
                'error': f'Error removing agency entries: {str(agency_delete_error)}'
            }), 500
        
        # Delete the booking
        try:
            db.session.delete(booking)
        except Exception as booking_delete_error:
            current_app.logger.error(f"Error deleting booking: {str(booking_delete_error)}")
            current_app.logger.error(traceback.format_exc())
            return jsonify({
                'success': False, 
                'error': f'Error deleting booking: {str(booking_delete_error)}'
            }), 500
        
        # Commit changes
        try:
            db.session.commit()
        except Exception as commit_error:
            db.session.rollback()
            current_app.logger.error(f"Error committing transaction: {str(commit_error)}")
            current_app.logger.error(traceback.format_exc())
            return jsonify({
                'success': False, 
                'error': f'Error committing transaction: {str(commit_error)}'
            }), 500
        
        # Log successful deletion with detailed information
        current_app.logger.info(
            f"Successfully deleted booking {booking_id}. "
            f"Car {car.id} is now available. "
            f"Removed {agency_car_status_count} agency car statuses and "
            f"{agency_visible_car_count} agency visible car entries."
        )
        
        return jsonify({
            'success': True
        }), 200
    
    except Exception as e:
        # Catch-all error handling
        db.session.rollback()
        
        # Extremely detailed error logging
        current_app.logger.error(
            f"Critical error deleting booking {booking_id}: {str(e)}\n"
            f"User: {current_user.id} ({current_user.name})\n"
            f"Full Traceback: {traceback.format_exc()}"
        )
        
        # Additional context logging
        try:
            import sys
            current_app.logger.error(f"Python version: {sys.version}")
            current_app.logger.error(f"Exception type: {type(e).__name__}")
        except Exception as log_error:
            current_app.logger.error(f"Error during additional logging: {log_error}")
        
        return jsonify({
            'success': False, 
            'error': f'An unexpected error occurred: {str(e)}'
        }), 500

@main.route('/maintenance')
@login_required
def maintenance():
    # Extremely verbose logging for debugging
    import traceback
    import sys
    from sqlalchemy.exc import SQLAlchemyError, DatabaseError
    
    # Log the start of the maintenance route access with maximum detail
    current_app.logger.info(
        f"Maintenance page access attempt. "
        f"User Details:\n"
        f"  ID: {current_user.id}\n"
        f"  Name: {current_user.name}\n"
        f"  Role: {current_user.role}\n"
        f"  Is Authenticated: {current_user.is_authenticated}\n"
        f"Python Version: {sys.version}\n"
        f"Current Working Directory: {os.getcwd()}"
    )
    
    # Validate user permissions early
    if not (current_user.is_admin or current_user.role in ['manager', 'secretary']):
        current_app.logger.warning(
            f"Unauthorized maintenance page access blocked. "
            f"User ID: {current_user.id}, Role: {current_user.role}"
        )
        flash('You do not have permission to access the maintenance page.', 'error')
        return redirect(url_for('main.dashboard'))
    
    # Comprehensive error handling with multiple fallback mechanisms
    try:
        # Validate database connection
        try:
            from sqlalchemy import text
            db.session.execute(text('SELECT 1'))
            current_app.logger.info("Database connection is active and responsive.")
        except Exception as db_connection_error:
            current_app.logger.critical(
                f"Database connection error: {str(db_connection_error)}\n"
                f"Full Traceback: {traceback.format_exc()}"
            )
            flash('Database connection error. Please contact support.', 'error')
            return redirect(url_for('main.dashboard'))
        
        # Fetch maintenance records with multiple error handling layers
        maintenance_records = []
        cars = []
        
        # Attempt to fetch maintenance records
        try:
            # Detailed query logging with SQLAlchemy error handling
            current_app.logger.info("Attempting to query maintenance records...")
            maintenance_records = Maintenance.query.order_by(Maintenance.created_at.desc()).all()
            
            # Safely handle None cost values
            for record in maintenance_records:
                if record.cost is None:
                    current_app.logger.warning(
                        f"Maintenance record {record.id} has a None cost value. "
                        f"Replacing with 0 to prevent rendering errors."
                    )
                    record.cost = 0
            
            current_app.logger.info(f"Successfully retrieved {len(maintenance_records)} maintenance records.")
        except SQLAlchemyError as maintenance_query_error:
            current_app.logger.error(
                f"Critical SQLAlchemy error querying maintenance records:\n"
                f"Error Type: {type(maintenance_query_error).__name__}\n"
                f"Error Details: {str(maintenance_query_error)}\n"
                f"Full Traceback: {traceback.format_exc()}"
            )
            # Additional logging of database connection state
            try:
                db.session.rollback()
                current_app.logger.info("Database session rolled back successfully.")
            except Exception as rollback_error:
                current_app.logger.error(f"Error during rollback: {str(rollback_error)}")
        
        # Attempt to fetch cars
        try:
            current_app.logger.info("Attempting to query cars...")
            cars = Car.query.all()
            current_app.logger.info(f"Successfully retrieved {len(cars)} cars.")
        except SQLAlchemyError as car_query_error:
            current_app.logger.error(
                f"Critical SQLAlchemy error querying cars:\n"
                f"Error Type: {type(car_query_error).__name__}\n"
                f"Error Details: {str(car_query_error)}\n"
                f"Full Traceback: {traceback.format_exc()}"
            )
        
        # Log query results with extensive details
        current_app.logger.info(
            f"Maintenance Page Query Results:\n"
            f"  Maintenance Records: {len(maintenance_records)}\n"
            f"  Cars: {len(cars)}\n"
            f"  User: {current_user.name} (ID: {current_user.id})\n"
            f"  Timestamp: {datetime.now()}"
        )
        
        # Render template with available data
        return render_template('maintenance.html', 
                             maintenance=maintenance_records,
                             cars=cars,
                             now=datetime.now())
    
    except Exception as critical_error:
        # Extremely detailed critical error logging
        current_app.logger.critical(
            f"CRITICAL ERROR in maintenance route:\n"
            f"Error: {str(critical_error)}\n"
            f"Error Type: {type(critical_error).__name__}\n"
            f"User Details:\n"
            f"  ID: {current_user.id}\n"
            f"  Name: {current_user.name}\n"
            f"  Role: {current_user.role}\n"
            f"Python Details:\n"
            f"  Version: {sys.version}\n"
            f"  Path: {sys.path}\n"
            f"Full Traceback:\n{traceback.format_exc()}"
        )
        
        # Additional context logging
        try:
            current_app.logger.error(f"Exception module: {critical_error.__class__.__module__}")
        except Exception as log_error:
            current_app.logger.error(f"Error during additional logging: {log_error}")
        
        # Provide a more informative error message
        flash(
            'A critical error occurred while accessing the maintenance page. '
            'Our team has been notified. Please try again later or contact support.', 
            'error'
        )
        return redirect(url_for('main.home'))

@main.route('/get_maintenance/<int:maintenance_id>')
@login_required
def get_maintenance(maintenance_id):
    try:
        # Check user permissions
        if not (current_user.is_admin or current_user.role in ['manager', 'secretary']):
            current_app.logger.warning(
                f"Unauthorized access to get maintenance details by user {current_user.id} with role {current_user.role}"
            )
            return jsonify({
                'success': False, 
                'error': 'You do not have permission to access maintenance details.'
            }), 403
        
        maintenance = Maintenance.query.get_or_404(maintenance_id)
        
        # Log maintenance details retrieval
        current_app.logger.info(
            f"Maintenance details retrieved: ID {maintenance_id}, "
            f"Car ID: {maintenance.car_id}, "
            f"Status: {maintenance.status}, "
            f"By user: {current_user.id} ({current_user.name})"
        )
        
        return jsonify({
            'success': True,
            'maintenance': {
                'id': maintenance.id,
                'car_id': maintenance.car_id,
                'status': maintenance.status,
                'issue_description': maintenance.issue_description,
                'start_date': maintenance.start_date.strftime('%Y-%m-%d'),
                'end_date': maintenance.end_date.strftime('%Y-%m-%d') if maintenance.end_date else None,
                'cost': maintenance.cost,
                'notes': maintenance.notes
            }
        })
    except Exception as e:
        current_app.logger.error(
            f"Error retrieving maintenance details for ID {maintenance_id}: {str(e)}", 
            exc_info=True
        )
        return jsonify({
            'success': False, 
            'error': 'An unexpected error occurred while retrieving maintenance details.'
        }), 500

@main.route('/add_maintenance', methods=['POST'])
@login_required
def add_maintenance():
    try:
        # Check user permissions
        if not (current_user.is_admin or current_user.role in ['manager', 'secretary']):
            current_app.logger.warning(
                f"Unauthorized maintenance addition by user {current_user.id} with role {current_user.role}"
            )
            return jsonify({
                'success': False, 
                'error': 'You do not have permission to add maintenance records.'
            }), 403
        
        # Validate input
        car_id = request.form.get('car_id')
        status = request.form.get('status')
        start_date = request.form.get('start_date')
        
        if not all([car_id, status, start_date]):
            current_app.logger.warning(
                f"Incomplete maintenance data submitted by user {current_user.id}"
            )
            return jsonify({
                'success': False, 
                'error': 'Missing required maintenance information.'
            }), 400
        
        # Validate car exists
        car = Car.query.get(car_id)
        if not car:
            current_app.logger.warning(
                f"Attempted to add maintenance for non-existent car {car_id}"
            )
            return jsonify({
                'success': False, 
                'error': 'Invalid car selected for maintenance.'
            }), 400
        
        maintenance = Maintenance(
            car_id=car_id,
            employee_id=current_user.id,
            status=status,
            issue_description=request.form.get('issue_description', ''),
            start_date=datetime.strptime(start_date, '%Y-%m-%d'),
            end_date=datetime.strptime(request.form.get('end_date'), '%Y-%m-%d') if request.form.get('end_date') else None,
            cost=float(request.form.get('cost')) if request.form.get('cost') else None,
            notes=request.form.get('notes', '')
        )
        
        # Update car status if maintenance is in progress
        if maintenance.status in ['pending', 'in_progress']:
            car.is_available = False
        
        db.session.add(maintenance)
        
        # Log maintenance addition
        current_app.logger.info(
            f"Maintenance record added: Car ID {car_id}, "
            f"Status {status}, "
            f"By user: {current_user.id} ({current_user.name})"
        )
        
        db.session.commit()
        return jsonify({'success': True})
        
    except ValueError as ve:
        current_app.logger.error(
            f"Invalid date or number format in maintenance addition: {str(ve)}", 
            exc_info=True
        )
        return jsonify({
            'success': False, 
            'error': 'Invalid date or cost format.'
        }), 400
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(
            f"Error adding maintenance record: {str(e)}", 
            exc_info=True
        )
        return jsonify({
            'success': False, 
            'error': 'An unexpected error occurred while adding maintenance record.'
        }), 500

@main.route('/update_maintenance/<int:maintenance_id>', methods=['POST'])
@login_required
def update_maintenance(maintenance_id):
    try:
        # Check user permissions
        if not (current_user.is_admin or current_user.role in ['manager', 'secretary']):
            current_app.logger.warning(
                f"Unauthorized maintenance update by user {current_user.id} with role {current_user.role}"
            )
            return jsonify({
                'success': False, 
                'error': 'You do not have permission to update maintenance records.'
            }), 403
        
        maintenance = Maintenance.query.get_or_404(maintenance_id)
        
        # Validate input
        car_id = request.form.get('car_id')
        status = request.form.get('status')
        start_date = request.form.get('start_date')
        
        if not all([car_id, status, start_date]):
            current_app.logger.warning(
                f"Incomplete maintenance data submitted by user {current_user.id}"
            )
            return jsonify({
                'success': False, 
                'error': 'Missing required maintenance information.'
            }), 400
        
        # Validate car exists
        car = Car.query.get(car_id)
        if not car:
            current_app.logger.warning(
                f"Attempted to update maintenance for non-existent car {car_id}"
            )
            return jsonify({
                'success': False, 
                'error': 'Invalid car selected for maintenance.'
            }), 400
        
        maintenance.car_id = car_id
        maintenance.status = status
        maintenance.issue_description = request.form.get('issue_description', '')
        maintenance.start_date = datetime.strptime(start_date, '%Y-%m-%d')
        maintenance.end_date = datetime.strptime(request.form.get('end_date'), '%Y-%m-%d') if request.form.get('end_date') else None
        maintenance.cost = float(request.form.get('cost')) if request.form.get('cost') else None
        maintenance.notes = request.form.get('notes', '')
        
        # Update car status based on maintenance status
        if maintenance.status == 'completed':
            car.is_available = True
        else:
            car.is_available = False
        
        db.session.commit()
        return jsonify({'success': True})
        
    except ValueError as ve:
        current_app.logger.error(
            f"Invalid date or number format in maintenance update: {str(ve)}", 
            exc_info=True
        )
        return jsonify({
            'success': False, 
            'error': 'Invalid date or cost format.'
        }), 400
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(
            f"Error updating maintenance record: {str(e)}", 
            exc_info=True
        )
        return jsonify({
            'success': False, 
            'error': 'An unexpected error occurred while updating maintenance record.'
        }), 500

@main.route('/delete_maintenance/<int:maintenance_id>', methods=['POST'])
@login_required
def delete_maintenance(maintenance_id):
    try:
        # Check user permissions
        if not (current_user.is_admin or current_user.role in ['manager', 'secretary']):
            current_app.logger.warning(
                f"Unauthorized maintenance deletion by user {current_user.id} with role {current_user.role}"
            )
            return jsonify({
                'success': False, 
                'error': 'You do not have permission to delete maintenance records.'
            }), 403
        
        maintenance = Maintenance.query.get_or_404(maintenance_id)
        
        # Make car available if it was under maintenance
        if maintenance.status in ['pending', 'in_progress']:
            car = Car.query.get(maintenance.car_id)
            car.is_available = True
        
        db.session.delete(maintenance)
        db.session.commit()
        return jsonify({'success': True})
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(
            f"Error deleting maintenance record: {str(e)}", 
            exc_info=True
        )
        return jsonify({
            'success': False, 
            'error': 'An unexpected error occurred while deleting maintenance record.'
        }), 500

@main.route('/financial_summary')
@login_required
def financial_summary():
    # Only admin and manager can access financial summary
    if not (current_user.is_admin or current_user.role == 'manager'):
        flash('Access denied. Only managers and administrators can access Financial Summary.', 'danger')
        return redirect(url_for('main.dashboard'))

    # Get current date
    today = datetime.now()

    # Get selected month and year from query parameters
    selected_month = request.args.get('month', today.month, type=int)
    selected_year = request.args.get('year', today.year, type=int)

    # Query for bookings in the selected month
    bookings = Booking.query.filter(
        extract('year', Booking.start_date) == selected_year,
        extract('month', Booking.start_date) == selected_month
    ).all()

    # Calculate financial metrics
    total_bookings = len(bookings)
    total_revenue = sum(booking.total_cost for booking in bookings)
    total_deposit = sum(booking.deposit_amount for booking in bookings)

    # Calculate total rental income for the year
    start_of_year = today.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    yearly_bookings = Booking.query.filter(Booking.start_date >= start_of_year).all()
    total_rental_income = sum(booking.total_cost for booking in yearly_bookings)

    # Calculate maintenance expenses for the year
    maintenance_records = Maintenance.query.filter(Maintenance.start_date >= start_of_year).all()
    total_maintenance_expense = sum(record.cost for record in maintenance_records if record.cost)

    # Monthly rental income trend
    monthly_rental_income = {}
    for month in range(1, 13):
        month_start = today.replace(month=month, day=1, hour=0, minute=0, second=0, microsecond=0)
        month_end = month_start.replace(month=month % 12 + 1, day=1) - timedelta(days=1)
        
        month_bookings = Booking.query.filter(
            Booking.start_date >= month_start,
            Booking.start_date <= month_end
        ).all()
        
        monthly_rental_income[month] = sum(booking.total_cost for booking in month_bookings)

    # Car rental performance
    car_performance = {}
    for car in Car.query.all():
        car_bookings = Booking.query.filter_by(car_id=car.id).all()
        car_performance[car.id] = {
            'model': car.model,
            'total_rentals': len(car_bookings),
            'total_income': sum(booking.total_cost for booking in car_bookings)
        }

    # Prepare context
    context = {
        'bookings': bookings,
        'total_bookings': total_bookings,
        'total_revenue': total_revenue,
        'total_deposit': total_deposit,
        'selected_month': selected_month,
        'selected_year': selected_year,
        'months': range(1, 13),
        'today': today,
        
        # Add back the previously calculated variables
        'total_rental_income': total_rental_income,
        'total_maintenance_expense': total_maintenance_expense,
        'net_income': total_rental_income - total_maintenance_expense,
        'monthly_rental_income': monthly_rental_income,
        'car_performance': car_performance,
        'total_maintenance_records': len(maintenance_records)
    }

    return render_template('financial_summary.html', **context)

@main.route('/expense_management', methods=['GET'])
@login_required
def expense_management():
    # Only admin and secretary can access expense management
    if not (current_user.is_admin or current_user.role == 'secretary'):
        flash('Access denied. Only administrators and secretaries can access expense management.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    # Get selected month and year from query parameters
    selected_month = request.args.get('month', datetime.now().month, type=int)
    selected_year = request.args.get('year', datetime.now().year, type=int)

    # Fetch expenses for the selected month and year
    expenses = Expense.query.filter(
        extract('year', Expense.date) == selected_year,
        extract('month', Expense.date) == selected_month
    ).order_by(Expense.date.desc()).all()

    # Calculate total expenses
    total_expenses = sum(expense.amount for expense in expenses)

    # Calculate summary by category
    category_totals = {}
    for expense in expenses:
        category_totals[expense.category] = category_totals.get(expense.category, 0) + expense.amount

    # Prepare context
    context = {
        'expenses': expenses,
        'total_expenses': total_expenses,
        'category_totals': category_totals,
        'selected_month': selected_month,
        'selected_year': selected_year,
        'months': [
            (1, 'January'), (2, 'February'), (3, 'March'), 
            (4, 'April'), (5, 'May'), (6, 'June'), 
            (7, 'July'), (8, 'August'), (9, 'September'), 
            (10, 'October'), (11, 'November'), (12, 'December')
        ]
    }

    return render_template('expense_management.html', **context)

@main.route('/income_management')
@secretary_or_admin_required
def view_income_management():
    # Get selected month and year from query parameters
    selected_month = request.args.get('month', datetime.now().month, type=int)
    selected_year = request.args.get('year', datetime.now().year, type=int)

    # Fetch incomes for the selected month and year
    incomes = Income.query.filter(
        extract('year', Income.date) == selected_year,
        extract('month', Income.date) == selected_month
    ).order_by(Income.date.desc()).all()

    # Calculate total incomes
    total_incomes = sum(income.amount for income in incomes)

    # Calculate summary by category
    category_totals = {}
    for income in incomes:
        category_totals[income.category] = category_totals.get(income.category, 0) + income.amount

    # Prepare context
    context = {
        'incomes': incomes,
        'total_incomes': total_incomes,
        'total_income': total_incomes,  # Add this line to match the template's expectation
        'category_totals': category_totals,
        'selected_month': selected_month,
        'selected_year': selected_year,
        'months': [
            (1, 'January'), (2, 'February'), (3, 'March'), 
            (4, 'April'), (5, 'May'), (6, 'June'), 
            (7, 'July'), (8, 'August'), (9, 'September'), 
            (10, 'October'), (11, 'November'), (12, 'December')
        ]
    }

    return render_template('income_management.html', **context)

@main.route('/add_income', methods=['POST'])
@login_required
def add_income():
    # Only admin or secretary can add income
    if not (current_user.is_admin or current_user.role == 'secretary'):
        return jsonify({'error': 'Only administrators or secretaries can add income'}), 403
    
    try:
        # Get form data
        category = request.form.get('category')
        amount = float(request.form.get('amount'))
        description = request.form.get('description')
        subcategory = request.form.get('subcategory', None)  # Optional subcategory
        
        # Validate input
        if not category or not amount:
            return jsonify({'error': 'Category and amount are required'}), 400
        
        # Create new income
        new_income = Income(
            category=category,
            amount=amount,
            description=description,
            subcategory=subcategory,  # Add subcategory
            user_id=current_user.id
        )
        
        # Add to database
        db.session.add(new_income)
        db.session.commit()
        
        return jsonify(new_income.to_dict()), 201
    
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Error adding income: {str(e)}')
        return jsonify({'error': 'Failed to add income'}), 500

@main.route('/update_income/<int:income_id>', methods=['POST'])
@login_required
def update_income(income_id):
    # Only admin or secretary can update income
    if not (current_user.is_admin or current_user.role == 'secretary'):
        return jsonify({'error': 'Only administrators or secretaries can update income'}), 403
    
    try:
        # Find existing income
        income = Income.query.get_or_404(income_id)
        
        # Get form data
        category = request.form.get('category')
        amount = float(request.form.get('amount'))
        description = request.form.get('description')
        subcategory = request.form.get('subcategory', None)  # Optional subcategory
        
        # Validate input
        if not category or not amount:
            return jsonify({'error': 'Category and amount are required'}), 400
        
        # Update income
        income.category = category
        income.amount = amount
        income.description = description
        income.subcategory = subcategory  # Update subcategory
        
        # Commit changes
        db.session.commit()
        
        return jsonify(income.to_dict()), 200
    
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Error updating income: {str(e)}')
        return jsonify({'error': 'Failed to update income'}), 500

@main.route('/delete_income/<int:income_id>', methods=['POST'])
@login_required
def delete_income(income_id):
    income = Income.query.get_or_404(income_id)
    
    db.session.delete(income)
    db.session.commit()
    
    return jsonify({'message': 'Income deleted successfully'}), 200

@main.route('/add_expense', methods=['POST'])
@login_required
def add_expense():
    # Only admin and secretary can add expenses
    if not (current_user.is_admin or current_user.role == 'secretary'):
        return jsonify({'error': 'Only administrators and secretaries can add expenses'}), 403
    
    data = request.form
    
    # Validate input
    if not all(key in data for key in ['amount', 'category', 'description']):
        return jsonify({'error': 'Missing required fields'}), 400
    
    try:
        amount = float(data['amount'])
        category = data['category']
        description = data['description']
        
        # Make subcategory optional, default to 'Other' if not provided
        subcategory = data.get('subcategory', 'Other')
        
        # If category is 'Other' and no subcategory is provided, use 'Other'
        if category == 'Other' and not subcategory:
            subcategory = 'Other'
    except ValueError:
        return jsonify({'error': 'Invalid amount'}), 400
    
    # Create new expense
    expense = Expense(
        amount=amount,
        category=category,
        subcategory=subcategory,
        description=description,
        user_id=current_user.id
    )
    
    try:
        db.session.add(expense)
        db.session.commit()
        return jsonify(expense.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error saving expense: {str(e)}")
        return jsonify({'error': f'Error saving expense: {str(e)}'}), 500

@main.route('/get_expense/<int:expense_id>')
@login_required
def get_expense(expense_id):
    expense = Expense.query.get_or_404(expense_id)
    return jsonify(expense.to_dict())

@main.route('/update_expense/<int:expense_id>', methods=['POST'])
@login_required
def update_expense(expense_id):
    # Only admin and secretary can update expenses
    if not (current_user.is_admin or current_user.role == 'secretary'):
        return jsonify({'error': 'Only administrators and secretaries can update expenses'}), 403
    
    expense = Expense.query.get_or_404(expense_id)
    data = request.form
    
    # Update fields
    expense.amount = float(data.get('amount', expense.amount))
    expense.category = data.get('category', expense.category)
    expense.subcategory = data.get('subcategory', expense.subcategory)
    expense.description = data.get('description', expense.description)
    
    db.session.commit()
    
    return jsonify(expense.to_dict())

@main.route('/delete_expense/<int:expense_id>', methods=['POST'])
@login_required
def delete_expense(expense_id):
    # Only admin and secretary can delete expenses
    if not (current_user.is_admin or current_user.role == 'secretary'):
        return jsonify({'error': 'Only administrators and secretaries can delete expenses'}), 403
    
    expense = Expense.query.get_or_404(expense_id)
    
    db.session.delete(expense)
    db.session.commit()
    
    return jsonify({'message': 'Expense deleted successfully'}), 200

@main.route('/add_employee', methods=['GET', 'POST'])
@login_required
def add_employee():
    # Only admin can add employees
    if not current_user.is_admin:
        flash('Only administrators can add new employees.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    if request.method == 'POST':
        try:
            # Validate input
            name = request.form.get('name')
            email = request.form.get('email')
            employee_id = request.form.get('employee_id')
            password = request.form.get('password')
            role = request.form.get('role')
            salary = request.form.get('salary')
            phone_number = request.form.get('phone_number')
            is_active = request.form.get('is_active') == 'on'

            # Check if employee_id already exists
            existing_employee = User.query.filter_by(employee_id=employee_id).first()
            if existing_employee:
                flash('An employee with this Employee ID already exists.', 'danger')
                return redirect(url_for('main.add_employee'))

            # Hash the password
            hashed_password = generate_password_hash(password)

            # Create new employee user
            new_employee = User(
                name=name,
                email=email,
                employee_id=employee_id,
                password=hashed_password,
                role=role,
                salary=float(salary),
                phone_number=phone_number,
                is_active=is_active,
                is_admin=role == 'admin'
            )
            
            db.session.add(new_employee)
            db.session.commit()
            
            flash('Employee registered successfully!', 'success')
            return redirect(url_for('main.manage_employees'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error registering employee: {str(e)}', 'error')
            return redirect(url_for('main.add_employee'))
    
    return render_template('add_employee.html')

@main.route('/manage_employees', methods=['GET', 'POST'])
@login_required
def manage_employees():
    # Only admin and manager can manage employees
    if not (current_user.is_admin or current_user.role == 'manager'):
        flash('Access denied. Only administrators and managers can manage employees.', 'danger')
        return redirect(url_for('main.dashboard'))

    # Handle employee addition
    if request.method == 'POST':
        action = request.form.get('action')

        # Employee Update Logic
        if action == 'update_employee':
            try:
                employee_id = request.form.get('id')
                employee = User.query.get(employee_id)

                if not employee or employee.role == 'agency':
                    flash('Invalid employee selection.', 'danger')
                    return redirect(url_for('main.manage_employees'))

                employee.name = request.form.get('name')
                employee.email = request.form.get('email')
                employee.employee_id = request.form.get('employee_id')
                employee.role = request.form.get('role')
                employee.salary = float(request.form.get('salary'))
                employee.phone_number = request.form.get('phone_number') or None

                db.session.commit()
                flash('Employee updated successfully!', 'success')
                return redirect(url_for('main.manage_employees'))

            except Exception as e:
                db.session.rollback()
                flash(f'Error updating employee: {str(e)}', 'danger')
                return redirect(url_for('main.manage_employees'))
        
        # Agency Edit Logic
        elif action == 'edit_agency':
            try:
                agency_id = request.form.get('id')
                agency = User.query.get(agency_id)

                if not agency or agency.role != 'agency':
                    return jsonify({
                        'status': 'error', 
                        'message': 'Invalid agency selection.'
                    }), 400

                agency.name = request.form.get('name')
                agency.email = request.form.get('email')
                agency.employee_id = request.form.get('employee_id')
                agency.phone_number = request.form.get('phone_number') or None
                agency.is_active = request.form.get('status') == 'active'

                db.session.commit()

                return jsonify({
                    'status': 'success', 
                    'message': 'Agency updated successfully!',
                    'agency': {
                        'id': agency.id,
                        'name': agency.name,
                        'email': agency.email,
                        'employee_id': agency.employee_id,
                        'phone_number': agency.phone_number,
                        'is_active': agency.is_active
                    }
                })
            except Exception as e:
                db.session.rollback()
                return jsonify({
                    'status': 'error', 
                    'message': f'Error updating agency: {str(e)}'
                }), 500

    # GET request: Fetch employees, agencies, and cars
    # Fetch all users and log detailed information
    all_users = User.query.all()
    current_app.logger.info("DEBUG: Total number of users: %d", len(all_users))
    
    # Detailed logging for all users
    for user in all_users:
        current_app.logger.info(
            "DEBUG User Details: ID=%d, Name=%s, Email=%s, Role=%s, Is Admin=%s, Is Active=%s", 
            user.id, user.name, user.email, user.role, user.is_admin, user.is_active
        )
    
    # Fetch employees with multiple filtering approaches
    employees_query = User.query
    
    # Try different filtering strategies
    employees = employees_query.filter(
        User.role != 'agency'
    ).all()
    
    current_app.logger.info("DEBUG: Number of employees after filtering: %d", len(employees))
    
    # Log details of filtered employees
    for employee in employees:
        current_app.logger.info(
            "DEBUG Filtered Employee: ID=%d, Name=%s, Email=%s, Role=%s, Is Admin=%s", 
            employee.id, employee.name, employee.email, employee.role, employee.is_admin
        )
    
    agencies = User.query.filter_by(role='agency').all()
    
    # Get IDs of cars already assigned to agencies
    assigned_car_ids = db.session.query(AgencyVisibleCar.car_id).distinct().all()
    assigned_car_ids = [car_id[0] for car_id in assigned_car_ids]
    
    # Filter out cars already assigned to agencies
    cars = Car.query.filter(~Car.id.in_(assigned_car_ids)).all()

    return render_template('manage_employees.html', 
                           employees=employees, 
                           agencies=agencies, 
                           cars=cars)

@main.route('/delete_employee/<int:employee_id>', methods=['POST'])
@login_required
def delete_employee(employee_id):
    # Check if it's an AJAX request
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    
    # Only admin can delete employees
    if not current_user.is_admin:
        error_response = {
            'status': 'error', 
            'message': 'Only administrators can delete employees.'
        }
        return jsonify(error_response), 403 if is_ajax else (
            flash('Only administrators can delete employees.', 'danger'),
            redirect(url_for('main.manage_employees'))
        )
    
    # Prevent deleting the current admin user
    if employee_id == current_user.id:
        error_response = {
            'status': 'error', 
            'message': 'You cannot delete your own account.'
        }
        return jsonify(error_response), 400 if is_ajax else (
            flash('You cannot delete your own account.', 'danger'),
            redirect(url_for('main.manage_employees'))
        )
    
    # Find the employee
    employee = User.query.get(employee_id)
    if not employee:
        error_response = {
            'status': 'error', 
            'message': 'Employee not found.'
        }
        return jsonify(error_response), 404 if is_ajax else (
            flash('Employee not found.', 'danger'),
            redirect(url_for('main.manage_employees'))
        )
    
    try:
        # Check for any existing bookings or dependencies
        existing_bookings = Booking.query.filter_by(employee_id=employee_id).count()
        if existing_bookings > 0:
            error_response = {
                'status': 'error', 
                'message': f'Cannot delete employee. They have {existing_bookings} existing bookings.'
            }
            return jsonify(error_response), 400 if is_ajax else (
                flash(f'Cannot delete employee. They have {existing_bookings} existing bookings.', 'danger'),
                redirect(url_for('main.manage_employees'))
            )
        
        # Store employee details for response
        employee_details = {
            'id': employee.id,
            'name': employee.name,
            'email': employee.email
        }
        
        # Delete the employee
        db.session.delete(employee)
        db.session.commit()
        
        # Log successful deletion
        current_app.logger.info(f"Employee {employee_id} deleted successfully.")
        
        # Prepare success response
        success_response = {
            'status': 'success', 
            'message': 'Employee deleted successfully.',
            'employee': employee_details
        }
        
        return jsonify(success_response), 200 if is_ajax else (
            flash('Employee deleted successfully.', 'success'),
            redirect(url_for('main.manage_employees'))
        )
    
    except Exception as e:
        # Log the full error for debugging
        current_app.logger.error(f"Error deleting employee {employee_id}: {str(e)}", exc_info=True)
        db.session.rollback()
        error_response = {
            'status': 'error', 
            'message': f'Error deleting employee: {str(e)}'
        }
        return jsonify(error_response), 500 if is_ajax else (
            flash(f'Error deleting employee: {str(e)}', 'danger'),
            redirect(url_for('main.manage_employees'))
        )

@main.route('/manage_clients', methods=['GET', 'POST'])
@login_required
def manage_clients():
    # Only admin, manager, and secretary can manage clients
    if not (current_user.is_admin or current_user.role in ['manager', 'secretary']):
        flash('Access denied. Only administrators, managers, and secretaries can manage clients.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    # Handle client deletion
    if request.method == 'POST' and request.form.get('action') == 'delete':
        client_id = request.form.get('client_id')
        try:
            # Check for existing bookings
            existing_bookings = Booking.query.filter_by(customer_id=client_id).count()
            if existing_bookings > 0:
                flash(f'Cannot delete client. They have {existing_bookings} existing bookings.', 'danger')
                return redirect(url_for('main.manage_clients'))
            
            # Delete the client
            client = Customer.query.get(client_id)
            if client:
                db.session.delete(client)
                db.session.commit()
                flash('Client deleted successfully.', 'success')
            else:
                flash('Client not found.', 'danger')
        except Exception as e:
            db.session.rollback()
            flash(f'Error deleting client: {str(e)}', 'danger')
        
        return redirect(url_for('main.manage_clients'))
    
    # Get all clients with their booking details
    clients = Customer.query.all()
    client_details = []
    
    for client in clients:
        # Get total bookings and total amount spent
        bookings = Booking.query.filter_by(customer_id=client.id).all()
        total_bookings = len(bookings)
        total_amount_spent = sum(booking.total_cost for booking in bookings)
        
        # Get most recent booking
        most_recent_booking = max(bookings, key=lambda x: x.created_at) if bookings else None
        
        client_details.append({
            'client': client,
            'total_bookings': total_bookings,
            'total_amount_spent': total_amount_spent,
            'most_recent_booking': most_recent_booking
        })
    
    return render_template('manage_clients.html', client_details=client_details)

@main.route('/get_client_details/<int:client_id>', methods=['GET'])
@login_required
def get_client_details(client_id):
    # Only admin, manager, and secretary can view client details
    if not (current_user.is_admin or current_user.role in ['manager', 'secretary']):
        return jsonify({'error': 'Access denied'}), 403
    
    client = Customer.query.get_or_404(client_id)
    
    # Get booking details
    bookings = Booking.query.filter_by(customer_id=client_id).all()
    
    # Calculate total bookings and amount spent
    total_bookings = len(bookings)
    total_amount_spent = sum(booking.total_cost for booking in bookings)
    
    # Prepare booking details
    booking_details = []
    for booking in bookings:
        booking_details.append({
            'created_at': booking.created_at.strftime('%Y-%m-%d %H:%M'),
            'car_model': booking.car.model,
            'start_date': booking.start_date.strftime('%Y-%m-%d'),
            'end_date': booking.end_date.strftime('%Y-%m-%d'),
            'total_cost': booking.total_cost,
            'status': booking.status
        })
    
    return jsonify({
        'name': client.name,
        'phone': client.phone,
        'email': client.email,
        'address': client.address,
        'license_number': client.license_number,
        'nin_passport_number': client.nin_passport_number,
        'nationality': client.nationality,
        'total_bookings': total_bookings,
        'total_amount_spent': total_amount_spent,
        'bookings': booking_details
    })

@main.route('/manage_cars/update_order', methods=['POST'])
@login_required
@manager_or_admin_required
def update_car_order():
    try:
        car_ids = request.json
        
        # Update display order for each car
        for index, car_id in enumerate(car_ids, start=1):
            car = Car.query.get(car_id)
            if car:
                car.display_order = index
        
        db.session.commit()
        
        return jsonify({
            'message': 'Car order updated successfully',
            'status': 'success'
        }), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating car order: {str(e)}")
        return jsonify({
            'message': 'Failed to update car order',
            'status': 'error'
        }), 500

@main.route('/add_agency', methods=['POST'])
@secretary_or_admin_required
def add_agency():
    try:
        # Get form data
        name = request.form.get('name')
        email = request.form.get('email')
        # Check both agency_id and employee_id
        employee_id = request.form.get('employee_id') or request.form.get('agency_id')
        phone_number = request.form.get('phone_number', '')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        # Validate input
        if not name or not email or not employee_id:
            return jsonify({
                'status': 'error',
                'message': 'Name, email, and employee ID are required.'
            }), 400
        
        # Validate password
        if password != confirm_password:
            return jsonify({
                'status': 'error',
                'message': 'Passwords do not match.'
            }), 400
        
        # Check if email or employee ID already exists
        existing_email = User.query.filter_by(email=email).first()
        existing_employee_id = User.query.filter_by(employee_id=employee_id).first()
        
        if existing_email:
            return jsonify({
                'status': 'error',
                'message': 'An agency with this email already exists.'
            }), 400
        
        if existing_employee_id:
            return jsonify({
                'status': 'error',
                'message': 'An agency with this employee ID already exists.'
            }), 400
        
        # Hash the provided password
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        
        # Create new agency
        new_agency = User(
            name=name,
            email=email,
            employee_id=employee_id,
            password=hashed_password,
            role='agency',
            phone_number=phone_number,
            is_active=True
        )
        
        # Get selected car IDs
        selected_car_ids = request.form.getlist('visible_cars')
        
        # Add the new agency to the session
        db.session.add(new_agency)
        db.session.flush()  # This will populate the ID without committing
        
        # Add visible cars for the agency
        for car_id in selected_car_ids:
            visible_car = AgencyVisibleCar(
                agency_id=new_agency.id,
                car_id=int(car_id)
            )
            db.session.add(visible_car)
        
        # Commit changes
        db.session.commit()
        
        # Prepare agency data for response
        agency_data = {
            'id': new_agency.id,
            'name': new_agency.name,
            'email': new_agency.email,
            'employee_id': new_agency.employee_id,
            'phone_number': new_agency.phone_number,
            'is_active': new_agency.is_active,
            'visible_cars_count': len(selected_car_ids)
        }
        
        return jsonify({
            'status': 'success',
            'message': 'Agency added successfully.',
            'agency': agency_data
        }), 201
    
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error adding agency: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': f'An error occurred: {str(e)}'
        }), 500

@main.route('/edit_agency/<int:agency_id>', methods=['POST'])
@login_required
def edit_agency(agency_id):
    try:
        # Find the agency to edit
        agency = User.query.get_or_404(agency_id)
        
        # Get form data
        name = request.form.get('name')
        email = request.form.get('email')
        employee_id = request.form.get('employee_id')
        phone_number = request.form.get('phone_number', '')
        status = request.form.get('status')
        
        # Validate input
        if not name or not email or not employee_id:
            return jsonify({
                'status': 'error',
                'message': 'Name, email, and employee ID are required.'
            }), 400
        
        # Check if email or employee ID already exists (excluding current agency)
        existing_email = User.query.filter(
            (User.email == email) & (User.id != agency_id)
        ).first()
        
        if existing_email:
            return jsonify({
                'status': 'error',
                'message': 'Email is already in use by another agency.'
            }), 400
        
        # Check if employee ID already exists (excluding current agency)
        existing_employee_id = User.query.filter(
            (User.employee_id == employee_id) & (User.id != agency_id)
        ).first()
        
        if existing_employee_id:
            return jsonify({
                'status': 'error',
                'message': 'Employee ID is already in use by another agency.'
            }), 400
        
        # Update agency details
        agency.name = name
        agency.email = email
        agency.employee_id = employee_id
        agency.phone_number = phone_number
        agency.is_active = status == 'active'
        
        # Handle car visibility
        visible_car_ids = request.form.getlist('visible_cars')
        
        # Remove existing visible cars
        AgencyVisibleCar.query.filter_by(agency_id=agency_id).delete()
        
        # Add new visible cars
        for car_id in visible_car_ids:
            visible_car = AgencyVisibleCar(
                agency_id=agency_id, 
                car_id=int(car_id)
            )
            db.session.add(visible_car)
        
        # Commit changes
        db.session.commit()
        
        # Prepare response with updated agency details and visible cars
        visible_cars = [
            {
                'id': vc.car_id, 
                'model': vc.car.model, 
                'license_plate': vc.car.license_plate
            } 
            for vc in agency.agency_visible_cars
        ]
        
        return jsonify({
            'status': 'success',
            'message': 'Agency updated successfully.',
            'agency': {
                'id': agency.id,
                'name': agency.name,
                'email': agency.email,
                'employee_id': agency.employee_id,
                'phone_number': agency.phone_number,
                'is_active': agency.is_active,
                'visible_cars': visible_cars
            }
        }), 200
    
    except Exception as e:
        # Rollback in case of error
        db.session.rollback()
        
        # Log the error
        current_app.logger.error(f"Error editing agency {agency_id}: {str(e)}")
        
        return jsonify({
            'status': 'error',
            'message': 'An unexpected error occurred while updating the agency.'
        }), 500

@main.route('/delete_agency/<int:agency_id>', methods=['POST'])
@secretary_or_admin_required
def delete_agency(agency_id):
    try:
        # Find the agency to delete
        agency = User.query.get_or_404(agency_id)
        
        # Detailed logging of agency information
        current_app.logger.info(f"Attempting to delete agency: ID={agency_id}, Name={agency.name}, Email={agency.email}")
        
        # Check if the agency has any active bookings created by its employees
        active_bookings_query = Booking.query.join(User, Booking.employee_id == User.id).filter(
            User.id == agency_id,
            Booking.status.in_(['pending', 'confirmed'])
        )
        active_bookings = active_bookings_query.all()
        
        if active_bookings:
            # Log details of active bookings
            booking_details = [
                f"Booking ID: {booking.id}, Status: {booking.status}, Car ID: {booking.car_id}" 
                for booking in active_bookings
            ]
            current_app.logger.warning(f"Cannot delete agency. Active bookings: {booking_details}")
            
            return jsonify({
                'status': 'error',
                'message': f'Cannot delete agency. There are {len(active_bookings)} active bookings created by this agency.',
                'booking_details': booking_details
            }), 400
        
        # Delete associated visible cars
        visible_car_ids = [vc.car_id for vc in AgencyVisibleCar.query.filter_by(agency_id=agency_id).all()]
        AgencyVisibleCar.query.filter_by(agency_id=agency_id).delete()
        current_app.logger.info(f"Deleted {len(visible_car_ids)} visible cars for agency {agency_id}")
        
        # Delete the agency
        db.session.delete(agency)
        db.session.commit()
        
        current_app.logger.info(f"Successfully deleted agency: ID={agency_id}, Name={agency.name}")
        
        return jsonify({
            'status': 'success',
            'message': f'Agency {agency.name} deleted successfully.'
        }), 200
    
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting agency: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': f'An unexpected error occurred: {str(e)}'
        }), 500

@main.route('/get_income/<int:income_id>')
@login_required
def get_income(income_id):
    income = Income.query.get_or_404(income_id)
    return jsonify(income.to_dict())

@main.route('/agency/update_car_status', methods=['POST'])
@login_required
def update_agency_car_status():
    # Ensure only agency users can update car status
    if current_user.role != 'agency':
        return jsonify({
            'status': 'error', 
            'message': 'Only agencies can update car status.'
        }), 403

    try:
        car_id = request.form.get('car_id')
        status = request.form.get('status')
        notes = request.form.get('notes', '')

        # Validate input
        if not car_id or status not in ['available', 'booked', 'unavailable']:
            return jsonify({
                'status': 'error', 
                'message': 'Invalid car or status.'
            }), 400

        # Check if the car is visible to this agency
        visible_car_ids = [vc.car_id for vc in current_user.agency_visible_cars]
        if int(car_id) not in visible_car_ids:
            return jsonify({
                'status': 'error', 
                'message': 'You do not have permission to update this car.'
            }), 403

        # Check if the car is unavailable
        car = Car.query.get(car_id)
        if not car.is_available:
            return jsonify({
                'status': 'error', 
                'message': 'Cannot change status. Car is currently unavailable.'
            }), 403

        # Check if the car is under maintenance
        active_maintenance = Maintenance.query.filter(
            Maintenance.car_id == car_id, 
            Maintenance.status.in_(['pending', 'in_progress'])
        ).first()

        if active_maintenance:
            return jsonify({
                'status': 'error', 
                'message': 'Cannot change status. Car is currently under maintenance.'
            }), 403

        # Check for active bookings by admin or manager
        active_booking = Booking.query.join(User, Booking.employee_id == User.id).filter(
            Booking.car_id == car_id,
            Booking.status == 'active',
            User.role.in_(['admin', 'manager'])
        ).first()

        if active_booking:
            return jsonify({
                'status': 'error', 
                'message': 'Car is currently booked by admin/manager and cannot be modified.'
            }), 403

        # Find or create agency car status
        agency_car_status = AgencyCarStatus.query.filter_by(
            agency_id=current_user.id, 
            car_id=car_id
        ).first()

        if agency_car_status:
            # Update existing status
            agency_car_status.status = status
            agency_car_status.notes = notes
        else:
            # Create new status
            agency_car_status = AgencyCarStatus(
                agency_id=current_user.id,
                car_id=car_id,
                status=status,
                notes=notes
            )
            db.session.add(agency_car_status)

        db.session.commit()

        return jsonify({
            'status': 'success', 
            'message': f'Car status updated to {status}.',
            'car_status': {
                'car_id': car_id,
                'status': status,
                'notes': notes
            }
        }), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating car status: {str(e)}")
        return jsonify({
            'status': 'error', 
            'message': f'Error updating car status: {str(e)}'
        }), 500

@main.route('/toggle_user_status', methods=['POST'])
@admin_required
def toggle_user_status():
    try:
        user_id = request.form.get('user_id')
        if not user_id:
            return jsonify({
                'status': 'error', 
                'message': 'User ID is required'
            }), 400
        
        user = User.query.get_or_404(user_id)
        
        # Toggle the user's active status
        user.is_active = not user.is_active
        db.session.commit()
        
        status = "activated" if user.is_active else "deactivated"
        flash(f'User {user.name} has been {status} successfully.', 'success')
        return jsonify({
            'status': 'success', 
            'message': f'User {status}', 
            'is_active': user.is_active
        }), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error toggling user status: {str(e)}")
        return jsonify({
            'status': 'error', 
            'message': f'Error toggling user status: {str(e)}'
        }), 500

@main.route('/activate_user', methods=['POST'])
@admin_required
def activate_user():
    try:
        user_id = request.form.get('user_id')
        user = User.query.get_or_404(user_id)
        
        # Activate the user
        user.is_active = True
        db.session.commit()
        
        flash(f'User {user.name} has been activated successfully.', 'success')
        return redirect(url_for('main.manage_employees'))
    except Exception as e:
        db.session.rollback()
        flash(f'Error activating user: {str(e)}', 'error')
        return redirect(url_for('main.manage_employees'))

@main.route('/edit_employee/<int:employee_id>', methods=['POST'])
@login_required
def edit_employee(employee_id):
    # Check if it's an AJAX request
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    
    # Only admin can edit employees
    if not current_user.is_admin:
        error_response = {
            'status': 'error', 
            'message': 'Only administrators can edit employees.'
        }
        return jsonify(error_response), 403 if is_ajax else (
            flash('Only administrators can edit employees.', 'danger'),
            redirect(url_for('main.manage_employees'))
        )
    
    # Find the employee
    employee = User.query.get_or_404(employee_id)
    
    try:
        # Get form data
        name = request.form.get('name')
        email = request.form.get('email')
        employee_id_input = request.form.get('employee_id')
        role = request.form.get('role')
        salary = request.form.get('salary')
        phone_number = request.form.get('phone_number')
        
        # Validate input
        if not all([name, email, employee_id_input]):
            error_response = {
                'status': 'error', 
                'message': 'Name, email, and employee ID are required.'
            }
            return jsonify(error_response), 400
        
        # Check if email is already in use by another employee
        existing_email = User.query.filter(
            User.email == email, 
            User.id != employee.id
        ).first()
        if existing_email:
            error_response = {
                'status': 'error', 
                'message': 'Email is already in use by another employee.'
            }
            return jsonify(error_response), 400
        
        # Check if employee_id is already in use by another employee
        existing_employee_id = User.query.filter(
            User.employee_id == employee_id_input, 
            User.id != employee.id
        ).first()
        if existing_employee_id:
            error_response = {
                'status': 'error', 
                'message': 'Employee ID is already in use.'
            }
            return jsonify(error_response), 400
        
        # Update employee details
        employee.name = name
        employee.email = email
        employee.employee_id = employee_id_input
        employee.role = role
        employee.salary = float(salary) if salary else 0.0
        employee.phone_number = phone_number
        
        # Commit changes
        db.session.commit()
        
        # Prepare success response
        success_response = {
            'status': 'success',
            'message': 'Employee updated successfully.',
            'employee': {
                'id': employee.id,
                'name': employee.name,
                'email': employee.email,
                'employee_id': employee.employee_id,
                'role': employee.role,
                'salary': employee.salary,
                'phone_number': employee.phone_number,
                'is_active': employee.is_active
            }
        }
        
        return jsonify(success_response), 200
    
    except Exception as e:
        # Rollback in case of error
        db.session.rollback()
        
        # Log the error
        current_app.logger.error(f"Error editing employee {employee_id}: {str(e)}")
        
        error_response = {
            'status': 'error', 
            'message': 'An unexpected error occurred while updating the employee.'
        }
        return jsonify(error_response), 500

@main.route('/get_agency_cars/<int:agency_id>', methods=['GET'])
@login_required
def get_agency_cars(agency_id):
    try:
        # Verify the agency exists
        agency = User.query.get_or_404(agency_id)
        
        # Ensure only admins and secretaries can view this
        if not (current_user.is_admin or current_user.role == 'secretary'):
            return jsonify({
                'status': 'error',
                'message': 'Unauthorized access'
            }), 403
        
        # Get all cars
        all_cars = Car.query.order_by(Car.model, Car.license_plate).all()
        
        # Get currently visible cars for this agency
        visible_car_ids = [vc.car_id for vc in AgencyVisibleCar.query.filter_by(agency_id=agency_id).all()]
        
        # Prepare car data
        car_data = [{
            'id': car.id,
            'model': car.model,
            'license_plate': car.license_plate
        } for car in all_cars]
        
        return jsonify({
            'status': 'success',
            'all_cars': car_data,
            'visible_car_ids': visible_car_ids
        }), 200
    
    except Exception as e:
        # Log the error
        current_app.logger.error(f"Error fetching agency cars: {str(e)}")
        
        return jsonify({
            'status': 'error',
            'message': 'An unexpected error occurred while fetching cars.'
        }), 500

@main.route('/favicon.ico')
def favicon():
    try:
        return send_from_directory(
            os.path.join(current_app.root_path, 'static'), 
            'favicon.ico', 
            mimetype='image/vnd.microsoft.icon'
        )
    except Exception as e:
        current_app.logger.error(f"Favicon error: {str(e)}", exc_info=True)
        return '', 404
