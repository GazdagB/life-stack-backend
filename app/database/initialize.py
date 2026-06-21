import psycopg
import dotenv
import os
from pathlib import Path
from typing import LiteralString,cast
from passlib.context import CryptContext


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

dotenv.load_dotenv()

schema_path = Path(__file__).with_name("schema.sql")
schema_sql = cast(LiteralString, schema_path.read_text())

seed_path = ( Path(__file__).with_name("seed.sql"))
seed_sql = cast(LiteralString, seed_path.read_text())

password = os.environ["USER_PASSWORD"]

hashed = pwd_context.hash(password)
email = os.environ["USER_EMAIL"]
username = os.environ["USER_NAME"]


with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
    with conn.cursor() as cur:
        try:


            cur.execute(schema_sql)
            print('✅ Database initilaized with schema.sql')
            cur.execute(
                """INSERT INTO users (username, email, password_hash)
                   VALUES (%s, %s, %s)
                """,
                (username, email, hashed)
            )
            print("✅ Admin user created successfully")
            cur.execute(seed_sql)
            print('✅ Database populated with mocked data using: seed.sql')

        except psycopg.Error as error:
            print(f'❌ Database Init and seeding failed: {error} ')