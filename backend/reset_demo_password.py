import sqlite3
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def main():
    conn = sqlite3.connect('knowledgepilot.db')
    cursor = conn.cursor()
    
    hashed = pwd_context.hash("password123")
    
    emails = [
        'demo1780804851699@knowledgepilot.demo',
        'chattest@test.com',
        'demotest100@test.com',
        'demotest101@test.com'
    ]
    
    print("Resetting passwords for demo users...")
    for email in emails:
        cursor.execute("UPDATE users SET hashed_password = ? WHERE email = ?", (hashed, email))
        if cursor.rowcount > 0:
            print(f"Updated password for {email} to 'password123'")
        else:
            print(f"User {email} not found in DB")
            
    conn.commit()
    conn.close()
    print("Done!")

if __name__ == "__main__":
    main()
