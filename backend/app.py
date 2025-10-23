from flask import Flask
from flask_cors import CORS
from db import engine, Base
from routes.job_routes import bp as job_bp
from config import PORT

# ✨ NEW
from flasgger import Swagger

def create_app():
    app = Flask(__name__)
    CORS(app)
    Base.metadata.create_all(engine)
    app.register_blueprint(job_bp)

    # ✨ NEW: simple Swagger config (shows at /apidocs)
    Swagger(app, template={
        "info": {"title": "Bitbash Jobs API", "version": "1.0.0"},
        "basePath": "/"
    })

    return app

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT, debug=True)
