from flask import Flask
from extensions import init_db
 
def create_app():
    app = Flask(__name__)
    db = init_db()
    app.db = db  # accessible as current_app.db in routes if needed
 
    @app.route("/api/health")
    def health():
        # simple check: ping the DB
        db.command("ping")
        return {"status": "ok", "db": "connected"}
 
    return app
 
 
if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)
 