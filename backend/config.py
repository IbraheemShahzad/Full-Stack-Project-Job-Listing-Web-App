import os
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.getenv("DB_URL", "postgresql+psycopg2://bitbash:bitbash@localhost:5432/bitbash_jobs")
PORT = int(os.getenv("PORT", "5001"))
