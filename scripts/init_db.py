import os
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

DB_NAME = os.getenv("DB_NAME", "detect_image_product")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

def create_database():
  try:
    conn = psycopg2.connect(
      dbname="postgres",
      user=DB_USER,
      password=DB_PASSWORD,
      host=DB_HOST,
      port=DB_PORT
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cursor = conn.cursor()

    cursor.execute(f"SELECT 1 FROM pg_database WHERE datname='{DB_NAME}'")
    if not cursor.fetchone():
      cursor.execute(f"CREATE DATABASE {DB_NAME}")
      print(f"Database '{DB_NAME}' created successfully.")

    cursor.execute(f"SELECT 1 FROM pg_roles WHERE rolname='{DB_USER}'")
    if not cursor.fetchone():
      cursor.execute(f"CREATE ROLE {DB_USER} WITH LOGIN PASSWORD '{DB_PASSWORD}'")
      print(f"User '{DB_USER}' created successfully.")

    cursor.execute(f"ALTER DATABASE {DB_NAME} OWNER TO {DB_USER}")
    cursor.execute(f"GRANT ALL PRIVILEGES ON DATABASE {DB_NAME} TO {DB_USER}")

    cursor.close()
    conn.close()

    conn = psycopg2.connect(
      dbname=DB_NAME,
      user=DB_USER,
      password=DB_PASSWORD,
      host=DB_HOST,
      port=DB_PORT
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cursor = conn.cursor()

    cursor.execute("CREATE EXTENSION IF NOT EXISTS vector")
    print("Extension 'pgvector' created successfully.")

    cursor.close()
    conn.close()

  except Exception as e:
    print(f"Error creating database: {e}")
  finally:
    if conn:
      conn.close()
    if cursor:
      cursor.close()
    print("Database connection closed.")

if __name__ == "__main__":
  create_database()