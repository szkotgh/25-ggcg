import sqlite3

def get_db_connection():
    conn = sqlite3.connect('db/main.db')
    conn.row_factory = sqlite3.Row
    return conn

def close_db_connection(conn):
    if conn:
        conn.close()
        
def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.executescript('''
        CREATE TABLE IF NOT EXISTS email_verification (
            email TEXT PRIMARY KEY,
            verification_code TEXT NOT NULL,
            is_verified BOOLEAN NOT NULL DEFAULT 0,
            try_count INTEGER NOT NULL DEFAULT 0,
            updated_at TIMESTAMP DEFAULT (datetime('now', '+9 hours')),
            created_at TIMESTAMP DEFAULT (datetime('now', '+9 hours'))
        );
        
        CREATE TABLE IF NOT EXISTS users (
            uid TEXT PRIMARY KEY,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            salt TEXT NOT NULL,
            name TEXT NOT NULL,
            profile_url TEXT DEFAULT NULL,
            created_at TIMESTAMP DEFAULT (datetime('now', '+9 hours')),
            FOREIGN KEY (email) REFERENCES email_verification(email)
        );
        
        CREATE TABLE IF NOT EXISTS user_sessions (
            sid TEXT PRIMARY KEY,
            uid TEXT NOT NULL,
            user_agent TEXT NOT NULL,
            ip_address TEXT NOT NULL,
            is_active BOOLEAN NOT NULL DEFAULT 1,
            last_accessed TIMESTAMP DEFAULT (datetime('now', '+9 hours')),
            update_at TIMESTAMP DEFAULT (datetime('now', '+9 hours')),
            expires_at TIMESTAMP NOT NULL,
            created_at TIMESTAMP DEFAULT (datetime('now', '+9 hours')),
            FOREIGN KEY (uid) REFERENCES users(uid)
        );
        
        CREATE TABLE IF NOT EXISTS foods (
            fid TEXT PRIMARY KEY,
            uid TEXT NOT NULL,
            name TEXT NOT NULL,
            type TEXT NOT NULL,
            description TEXT NOT NULL,
            count INTEGER NOT NULL DEFAULT 0,
            volume TEXT DEFAULT NULL,
            image_url TEXT DEFAULT NULL,
            barcode TEXT NOT NULL,
            expiration_date_desc TEXT,
            expiration_date DATE NOT NULL,
            created_at TIMESTAMP DEFAULT (datetime('now', '+9 hours')),
            FOREIGN KEY (uid) REFERENCES users(uid)
        );
    ''')
    
    conn.commit()
    close_db_connection(conn)
    
init_db()