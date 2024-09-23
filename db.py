import mysql.connector
import os
import dotenv

dotenv.load_dotenv()

# Connect to MySQL Database
def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv("MYSQL_HOST", "localhost"),
        user=os.getenv("MYSQL_USER"),
        password=os.getenv("MYSQL_PASSWORD"),
        database=os.getenv("MYSQL_DATABASE")
    )

# Initialize the database and create the users table
def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Separate SQL statements
    create_users_table = '''
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(255) NOT NULL UNIQUE,
            email VARCHAR(255) NOT NULL UNIQUE,
            password_hash VARCHAR(255) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    '''

    create_api_usage_table = '''
        CREATE TABLE IF NOT EXISTS api_usage (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_email VARCHAR(255) NOT NULL,
            api_endpoint VARCHAR(255) NOT NULL,
            usage_count INT DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_email) REFERENCES users(email)
        )
    '''
    
    create_api_usage_table = '''
        CREATE TABLE IF NOT EXISTS api_usage (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_email VARCHAR(255) NOT NULL,
            api_endpoint VARCHAR(255) NOT NULL,
            usage_count INT DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_email) REFERENCES users(email),
            UNIQUE KEY (user_email, api_endpoint)  -- Add unique constraint here
        )
    '''

    

    # Execute each statement separately
    cursor.execute(create_users_table)
    cursor.execute(create_api_usage_table)
    
    conn.commit()
    cursor.close()
    conn.close()