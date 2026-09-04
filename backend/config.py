

import os
from dotenv import load_dotenv

load_dotenv()  # reads .env in the project root, if present


class Config:
    MONGODB_URI = os.environ.get("MONGODB_URI")
    SECRET_KEY = os.environ.get("FLASK_SECRET_KEY")
    ENV = os.environ.get("FLASK_ENV", "development")

    @staticmethod
    def validate():
        """Fail loudly at startup if required secrets are missing,
        instead of failing confusingly later mid-request."""
        missing = []
        if not Config.MONGODB_URI:
            missing.append("MONGODB_URI")
        if not Config.SECRET_KEY:
            missing.append("FLASK_SECRET_KEY")
        if missing:
            raise RuntimeError(
                f"Missing required environment variables: {', '.join(missing)}. "
                f"Did you create a .env file from .env.example?"
            )