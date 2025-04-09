import os
import secrets

from flask import Flask
from flask_jwt_extended import JWTManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

# Initialize the app
app = Flask(__name__)

# Load configuration from environment variables
app.config["SQLALCHEMY_DATABASE_URI"] = (
    "postgresql://postgres:indomitable@localhost:5432/blog_api"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = secrets.token_hex(16)


# Initialize extensions
db = SQLAlchemy(app)
migrate = Migrate(app, db)
jwt = JWTManager(app)

# Import models and routes to register them with the app
from app import models, routes
