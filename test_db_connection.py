import os
import sys
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_database_connection():
    """
    Test database connection and perform basic operations
    """
    try:
        # Explicitly load .env file
        env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
        load_dotenv(env_path)
        
        # Hardcoded PostgreSQL URL from .env
        database_url = "postgresql://carrent_db_9jzj_user:k8Ea39rP0FR8WDuSOgtt5wdteqwISTbd@dpg-cujqqlggph6c73bkmedg-a.oregon-postgres.render.com/carrent_db_9jzj"
        
        if not database_url:
            logger.error("DATABASE_URL is not set!")
            return False
        
        # Create SQLAlchemy engine with connection pooling and detailed logging
        engine = create_engine(
            database_url, 
            pool_pre_ping=True,
            echo=True  # Enable SQLAlchemy logging
        )
        
        # Attempt to connect
        with engine.connect() as connection:
            # Test query for PostgreSQL
            result = connection.execute(text("SELECT 1"))
            
            # Fetch the result
            scalar_result = result.scalar()
            
            if scalar_result == 1:
                logger.info("✅ Database connection successful!")
                
                # Additional connection details
                logger.info(f"Database URL: {database_url}")
                logger.info(f"Database Engine: {engine.driver}")
                
                # Optional: Test table creation and query
                try:
                    connection.execute(text("""
                        CREATE TABLE IF NOT EXISTS connection_test (
                            id SERIAL PRIMARY KEY,
                            test_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    """))
                    connection.execute(text("""
                        INSERT INTO connection_test DEFAULT VALUES
                    """))
                    logger.info("✅ Successfully created and inserted into test table")
                except Exception as table_error:
                    logger.warning(f"⚠️ Table creation/insertion test failed: {table_error}")
                
                return True
            else:
                logger.error("❌ Unexpected result from database connection test")
                return False
    
    except SQLAlchemyError as e:
        logger.error(f"❌ Database Connection Error: {type(e).__name__}: {e}")
        logger.error(f"Detailed Error: {sys.exc_info()}")
        return False
    except Exception as e:
        logger.error(f"❌ Unexpected Error: {type(e).__name__}: {e}")
        logger.error(f"Detailed Error: {sys.exc_info()}")
        return False

def main():
    """
    Main function to run database connection test
    """
    # Perform connection test
    connection_result = test_database_connection()
    
    # Exit with appropriate status code
    sys.exit(0 if connection_result else 1)

if __name__ == '__main__':
    main()
