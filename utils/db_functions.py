import mysql.connector
from db import get_db_connection


# Function to check API usage
def check_api_usage(email, endpoint):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute('''
            SELECT usage_count FROM api_usage 
            WHERE user_email = %s AND api_endpoint = %s
        ''', (email, endpoint))
        
        usage = cursor.fetchone()
        cursor.close()
        conn.close()
        return usage['usage_count'] if usage else 0
    except mysql.connector.Error as err:
        print(f"Database error: {err}")
        return None

# Function to update API usage
def update_api_usage(email, endpoint):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO api_usage (user_email, api_endpoint, usage_count) 
            VALUES (%s, %s, 1)
            ON DUPLICATE KEY UPDATE usage_count = usage_count + 1
        ''', (email, endpoint))

        conn.commit()
        cursor.close()
        conn.close()
    except mysql.connector.Error as err:
        print(f"Database error: {err}")
