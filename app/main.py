from flask import Flask
from flask_openapi3 import OpenAPI
from app.core.config import settings
from app.core.exceptions import APIError
from app.core.responses import ErrorResponse
import os
import socket
import time
import atexit


def is_port_in_use(port: int) -> bool:
    """Check if a port is already in use"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
    try:
        sock.bind(('0.0.0.0', port))
        sock.close()
        return False
    except socket.error:
        return True


def cleanup_socket(sock):
    """Ensure socket is properly closed"""
    try:
        sock.shutdown(socket.SHUT_RDWR)
    except:
        pass
    try:
        sock.close()
    except:
        pass


def create_app() -> Flask:
    """Create and configure Flask application"""
    # Only enable debugpy in main process (not Flask reloader)
    if settings.API_DEBUG and os.getenv('DEBUGPY_ENABLE') and not os.environ.get('WERKZEUG_RUN_MAIN'):
        try:
            import debugpy
            debugpy_port = int(os.getenv('DEBUGPY_PORT', '5678'))
            if not is_port_in_use(debugpy_port):
                debugpy.listen(('0.0.0.0', debugpy_port))
                print(f"🐛 Debugpy is listening on port {debugpy_port}")
        except ImportError:
            print("⚠️  Debugpy not installed. Install with: pip install debugpy")
        except Exception as e:
            print(f"⚠️  Failed to initialize debugger: {e}")

    app = OpenAPI(__name__)
    app.config.from_object(settings)

    # Register error handlers
    @app.errorhandler(APIError)
    def handle_api_error(error):
        return ErrorResponse(
            message=error.message,
            error={"code": error.code, "details": error.details}
        ).dict(), error.status_code or 400

    # Register blueprints
    from app.api.root import root_bp
    app.register_blueprint(root_bp)
    from app.api.v1 import api_v1
    app.register_blueprint(api_v1)

    return app
