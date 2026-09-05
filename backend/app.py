from flask import Flask
from extensions import init_db
from auth.routes import auth_bp


def create_app():
    app = Flask(__name__)

    db = init_db()
    app.db = db

    # Register authentication routes
    app.register_blueprint(auth_bp, url_prefix="/api/auth")

    @app.route("/api/health")
    def health():
        db.command("ping")
        return {"status": "ok", "db": "connected"}

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, port=5000)