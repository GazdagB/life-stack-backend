import psycopg
import dotenv
import os
from pathlib import Path
from typing import LiteralString,cast

dotenv.load_dotenv()

schema_path = Path(__file__).with_name("schema.sql")
schema_sql = cast(LiteralString, schema_path.read_text())

seed_path = ( Path(__file__).with_name("seed.sql"))
seed_sql = cast(LiteralString, seed_path.read_text())

with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
    with conn.cursor() as cur:
            cur.execute(schema_sql)
            cur.execute(seed_sql)