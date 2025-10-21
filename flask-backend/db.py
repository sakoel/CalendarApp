import json, sqlite3, os

DB_PATH = os.environ.get("DB_PATH", "app.db")

def _conn():
    c = sqlite3.connect(DB_PATH)
    c.execute("""
    CREATE TABLE IF NOT EXISTS user_creds(
      sub TEXT PRIMARY KEY,     -- stable Google user id
      email TEXT,
      creds_json TEXT NOT NULL  -- google Credentials.to_json()
    )
    """)
    return c

def save_user_creds(sub: str, email: str, creds_json: str):
    c = _conn()
    c.execute("REPLACE INTO user_creds(sub, email, creds_json) VALUES(?,?,?)",
              (sub, email, creds_json))
    c.commit(); c.close()

def get_user_creds(sub: str):
    c = _conn()
    row = c.execute("SELECT creds_json FROM user_creds WHERE sub=?", (sub,)).fetchone()
    c.close()
    return json.loads(row[0]) if row else None
