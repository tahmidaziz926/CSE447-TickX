from flask import Flask
from extensions import init_db
from auth.routes import auth_bp
from auth.profile_routes import profile_bp
from events.routes import events_bp
from tickets.routes import tickets_bp, transactions_bp
from admin.routes import admin_bp


def create_app():
    app = Flask(__name__)

    db = init_db()
    app.db = db

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(profile_bp, url_prefix="/api/auth")
    app.register_blueprint(events_bp, url_prefix="/api/events")
    app.register_blueprint(tickets_bp, url_prefix="/api/tickets")
    app.register_blueprint(transactions_bp, url_prefix="/api/transactions")
    app.register_blueprint(admin_bp, url_prefix="/api/admin")

    @app.route("/api/health")
    def health():
        db.command("ping")
        return {"status": "ok", "db": "connected"}

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, port=5000)