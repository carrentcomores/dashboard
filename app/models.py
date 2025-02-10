from . import db
from flask_login import UserMixin
from datetime import datetime

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), nullable=False)
    password = db.Column(db.String(255), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    employee_id = db.Column(db.String(100), unique=True, nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    role = db.Column(db.String(50), nullable=False, default='employee')  # 'admin', 'manager', 'secretary'
    salary = db.Column(db.Float, nullable=True, default=0.0)  # Employee salary
    phone_number = db.Column(db.String(50), nullable=True)  # Employee phone number
    is_active = db.Column(db.Boolean, default=True)  # New column for active/inactive status
    bookings_created = db.relationship('Booking', backref='employee', lazy=True)
    user_expenses = db.relationship('Expense', backref='user', lazy=True)
    user_incomes = db.relationship('Income', backref='user_income', lazy=True)

class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)
    address = db.Column(db.String(200), nullable=True)
    license_number = db.Column(db.String(50), nullable=False)
    nin_passport_number = db.Column(db.String(50), unique=True, nullable=True)
    nationality = db.Column(db.String(50), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    bookings = db.relationship('Booking', backref='customer', lazy='dynamic')

    @staticmethod
    def merge_duplicate_clients(db):
        """
        Find and merge clients with the same phone number.
        Keeps the client with the most complete information.
        """
        from sqlalchemy import func
        
        # Find phone numbers with multiple clients
        duplicate_phones = (
            db.session.query(Customer.phone)
            .group_by(Customer.phone)
            .having(func.count(Customer.id) > 1)
            .all()
        )
        
        merged_count = 0
        for (phone,) in duplicate_phones:
            # Get all clients with this phone number
            duplicate_clients = Customer.query.filter_by(phone=phone).order_by(
                # Prioritize clients with more complete information
                func.length(Customer.name).desc(),
                func.length(Customer.email).desc(),
                func.length(Customer.address).desc()
            ).all()
            
            # Skip if no duplicates or only one client
            if len(duplicate_clients) <= 1:
                continue
            
            # Keep the first (most complete) client
            primary_client = duplicate_clients[0]
            
            # Merge other clients into the primary client
            for secondary_client in duplicate_clients[1:]:
                # Transfer bookings to primary client
                bookings = Booking.query.filter_by(customer_id=secondary_client.id).all()
                for booking in bookings:
                    booking.customer_id = primary_client.id
                
                # Merge additional information if primary client's info is less complete
                if not primary_client.email and secondary_client.email:
                    primary_client.email = secondary_client.email
                
                if not primary_client.address and secondary_client.address:
                    primary_client.address = secondary_client.address
                
                # Delete the secondary client
                db.session.delete(secondary_client)
                
                # Increment merged count
                merged_count += 1
            
            # Commit changes
            db.session.commit()
        
        return merged_count

    def __repr__(self):
        return f'<Customer {self.name}>'

class Car(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    model = db.Column(db.String(100), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    license_plate = db.Column(db.String(20), unique=True, nullable=False)
    daily_rate = db.Column(db.Float, nullable=False)
    is_available = db.Column(db.Boolean, default=True)
    category = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text)
    features = db.Column(db.Text)  # Store as JSON string
    main_image = db.Column(db.String(500), nullable=True)  # Increased from 200 to 500
    display_order = db.Column(db.Integer, default=0)  # New field for custom ordering
    images = db.relationship('CarImage', backref='car', lazy=True, cascade='all, delete-orphan')
    bookings = db.relationship('Booking', backref='car', lazy=False)
    maintenance_records = db.relationship('Maintenance', backref='car', lazy=True, cascade='all, delete-orphan')

class CarImage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    car_id = db.Column(db.Integer, db.ForeignKey('car.id'), nullable=False)
    image_path = db.Column(db.String(500), nullable=False)  # Increased from 200 to 500
    caption = db.Column(db.String(200))
    is_main = db.Column(db.Boolean, default=False)
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)

class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)
    car_id = db.Column(db.Integer, db.ForeignKey('car.id'), nullable=False)
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=False)
    total_cost = db.Column(db.Float, nullable=False)
    deposit_amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='active')
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Maintenance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    car_id = db.Column(db.Integer, db.ForeignKey('car.id'), nullable=False)
    employee_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    issue_description = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, in_progress, completed
    cost = db.Column(db.Float, nullable=True)
    start_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    end_date = db.Column(db.DateTime, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    amount = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(50), nullable=False)  # e.g., 'Products', 'Bank', 'Salaries', 'Bills'
    subcategory = db.Column(db.String(100), nullable=False)  # e.g., 'Office Supplies', 'Electricity', 'Rent'
    description = db.Column(db.Text, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    def to_dict(self):
        return {
            'id': self.id,
            'date': self.date.strftime('%Y-%m-%d %H:%M'),
            'amount': self.amount,
            'category': self.category,
            'subcategory': self.subcategory,
            'description': self.description,
            'employee': self.user.name
        }

class Income(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    amount = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(50), nullable=False)  # 'Airport Transfer', 'Car Order', 'Partnership', 'Car Sell'
    subcategory = db.Column(db.String(50), nullable=True)  # New field for subcategory
    description = db.Column(db.Text, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    def to_dict(self):
        return {
            'id': self.id,
            'date': self.date.strftime('%Y-%m-%d %H:%M'),
            'amount': self.amount,
            'category': self.category,
            'subcategory': self.subcategory,  
            'description': self.description,
            'user_name': self.user_income.name
        }

class AgencyVisibleCar(db.Model):
    __tablename__ = 'agency_visible_cars'
    id = db.Column(db.Integer, primary_key=True)
    agency_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    car_id = db.Column(db.Integer, db.ForeignKey('car.id'), nullable=False)
    
    # Relationships
    agency = db.relationship('User', backref=db.backref('agency_visible_cars', cascade='all, delete-orphan'))
    car = db.relationship('Car', backref=db.backref('agency_visible_cars', cascade='all, delete-orphan'))
    
    # Ensure unique constraint to prevent duplicate entries
    __table_args__ = (db.UniqueConstraint('agency_id', 'car_id', name='_agency_car_uc'),)

class AgencyCarStatus(db.Model):
    __tablename__ = 'agency_car_status'
    id = db.Column(db.Integer, primary_key=True)
    agency_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    car_id = db.Column(db.Integer, db.ForeignKey('car.id'), nullable=False)
    status = db.Column(db.String(20), nullable=False, default='available')  # options: available, booked, unavailable
    notes = db.Column(db.Text, nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    agency = db.relationship('User', backref=db.backref('car_statuses', cascade='all, delete-orphan'))
    car = db.relationship('Car', backref=db.backref('agency_statuses', cascade='all, delete-orphan'))

    # Ensure unique constraint to prevent duplicate entries
    __table_args__ = (db.UniqueConstraint('agency_id', 'car_id', name='_agency_car_status_uc'),)
