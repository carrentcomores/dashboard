import os
import sys
from sqlalchemy import create_engine, text
from werkzeug.security import check_password_hash, generate_password_hash
from dotenv import load_dotenv

# Hardcoded PostgreSQL URL
DATABASE_URL = "postgresql://carrent_db_9jzj_user:k8Ea39rP0FR8WDuSOgtt5wdteqwISTbd@dpg-cujqqlggph6c73bkmedg-a.oregon-postgres.render.com/carrent_db_9jzj"

# Create engine
engine = create_engine(DATABASE_URL)

def check_admin_user():
    with engine.connect() as connection:
        # Query to find admin user
        result = connection.execute(text(
            "SELECT id, email, password FROM \"user\" WHERE email = 'admin@carrent.com'"
        ))
        user = result.fetchone()
        
        if user:
            print(f"User found:")
            print(f"ID: {user.id}")
            print(f"Email: {user.email}")
            print(f"Password Hash: {user.password}")
            
            # Test password verification
            test_passwords = [
                'CarRent2024!@#SecureAdmin',  # Current password
                'default_admin_password',     # Previous default password
                'your_local_development_secret_key'  # Old development key
            ]
            
            print("\nPassword Verification:")
            for pwd in test_passwords:
                is_match = check_password_hash(user.password, pwd)
                print(f"Password '{pwd}': {is_match}")
        else:
            print("No admin user found with email admin@carrent.com")

def create_admin_user():
    with engine.connect() as connection:
        # Generate a new secure password hash
        new_password = 'default_admin_password'
        password_hash = generate_password_hash(new_password, method='pbkdf2:sha256')
        
        # Update existing user or insert new user
        connection.execute(text("""
            UPDATE "user" 
            SET 
                password = :password, 
                is_admin = true, 
                role = 'admin', 
                name = 'System Administrator', 
                employee_id = 'ADMIN001', 
                is_active = true
            WHERE email = 'admin@carrent.com';
            
            INSERT INTO "user" (
                email, password, is_admin, role, name, employee_id, is_active
            )
            SELECT 
                'admin@carrent.com', 
                :password, 
                true, 
                'admin', 
                'System Administrator', 
                'ADMIN001', 
                true
            WHERE NOT EXISTS (
                SELECT 1 FROM "user" WHERE email = 'admin@carrent.com'
            );
        """), {
            'password': password_hash
        })
        connection.commit()
        print("Admin user created/updated successfully!")

def main():
    print("Checking existing admin user:")
    check_admin_user()
    
    print("\nCreating/Updating admin user:")
    create_admin_user()
    
    print("\nVerifying updated user:")
    check_admin_user()

if __name__ == '__main__':
    main()
