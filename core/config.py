import os

TOKEN = os.environ.get("DISCORD_TOKEN")
DATABASE_URL = os.environ.get("DATABASE_URL")
WEBSITE_URL = os.environ.get("WEBSITE_URL")
OWNER_ID = int(os.environ.get("OWNER_ID", "0"))

TOSS_CLIENT_KEY = os.environ.get("TOSS_CLIENT_KEY")
TOSS_SECRET_KEY = os.environ.get("TOSS_SECRET_KEY")