import os
from sqlalchemy import create_engine, text
from werkzeug.security import generate_password_hash

# Hardcoded PostgreSQL URL
DATABASE_URL = "postgresql://carrent_db_9jzj_user:k8Ea39rP0FR8WDuSOgtt5wdteqwISTbd@dpg-cujqqlggph6c73bkmedg-a.oregon-postgres.render.com/carrent_db_9jzj"

# Create engine
engine = create_engine(DATABASE_URL)

def update_admin_password(new_password):
    # Generate password hash
    password_hash = generate_password_hash(new_password, method='pbkdf2:sha256')
    
    with engine.connect() as connection:
        # Update admin user's password
        result = connection.execute(text("""
            UPDATE "user" 
            SET 
                password = :password
            WHERE email = 'admin@carrent.com';
        """), {
            'password': password_hash
        })
        connection.commit()
        
        print(f"Password updated for admin@carrent.com. Rows affected: {result.rowcount}")

def main():
    # New secure password
    new_password = 'CarRent2024!@#SecureAdmin'
    update_admin_password(new_password)
    print("Admin password has been reset. You can now log in with the new password.")

if __name__ == '__main__':
    main()
