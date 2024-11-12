from flask import Blueprint
from app.api.v1.endpoints.health import health_bp

api_v1 = Blueprint('api_v1', __name__, url_prefix='/v1')
api_v1.register_blueprint(health_bp)