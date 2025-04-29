import logging
from flask import Blueprint, send_from_directory
import os

static_bp = Blueprint('static_bp', __name__)

@static_bp.route('/custom-static/<path:filename>')
def serve_static(filename):
    static_dir = os.path.join(static_bp.root_path, '..', 'static')
    app_logger = logging.getLogger('app')
    app_logger.debug(f"Serving static file: {filename} from {static_dir}")
    return send_from_directory(static_dir, filename)