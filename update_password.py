#!/usr/bin/env python3
"""
Update user password in database
"""

import sys
import os
from pathlib import Path

# Add the src directory to Python path
sys.path.append('src')

from ai_rule_engine.database import DatabaseConnector

def main():
    try:
        # Initialize database connector (will use environment variables)
        db = DatabaseConnector()

        # New password hash for 'password123'
        new_hash = '$2b$12$mGEAXHjnf6rw0HqcPX5jDu677NmcrktZ5rruGed1yXXS9rNkVT11m'

        # Update the password
        with db.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE users
                    SET password_hash = %s
                    WHERE username = %s
                """, (new_hash, 'vohuy'))
                conn.commit()

                if cursor.rowcount > 0:
                    print("✓ Password updated successfully for user 'vohuy'")
                    print("✓ New password: password123")
                    print("✓ You can now login with username 'vohuy' and password 'password123'")
                else:
                    print("✗ User 'vohuy' not found in database")

    except Exception as e:
        print(f"Error updating password: {e}")
        print("Make sure your database environment variables are set correctly:")
        print("- DB_HOST")
        print("- DB_PORT")
        print("- DB_NAME")
        print("- DB_USER")
        print("- DB_PASSWORD")
        return 1

    return 0

if __name__ == "__main__":
    exit(main())
