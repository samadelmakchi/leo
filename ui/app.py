"""
فایل اصلی Flask Application
"""

from flask import Flask, render_template
import os
import sys
import logging

# تنظیم لاگ
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# لاگ کاربر فعلی
logger.info(f"Starting Flask app as user: {os.getenv('USER')}")
logger.info(f"Effective UID: {os.geteuid()}")
logger.info(f"Python path: {sys.path}")

# ایمپورت ماژول‌ها
try:
    logger.info("Attempting to import docker_module...")
    from docker_module import docker_bp
    logger.info("✅ docker_module imported successfully")
    
    logger.info("Attempting to import ansible_module...")
    from ansible_module import ansible_bp
    logger.info("✅ ansible_module imported successfully")
    
    logger.info("Attempting to import cron_module...")
    from cron_module import cron_bp
    logger.info("✅ cron_module imported successfully")
    
    # ثبت Blueprint ماژول‌ها
    app.register_blueprint(docker_bp)
    app.register_blueprint(ansible_bp)
    app.register_blueprint(cron_bp)
    logger.info("✅ All blueprints registered successfully")
    
    # تست Docker connection در startup
    try:
        from docker_module import get_docker_client
        client = get_docker_client()
        if client:
            info = client.info()
            logger.info(f"✅ Docker connection verified. Version: {info.get('ServerVersion')}")
        else:
            logger.warning("⚠️ Docker client is None on startup")
    except Exception as e:
        logger.error(f"❌ Docker connection test failed on startup: {e}")
    
except ImportError as e:
    logger.error(f"❌ Import error: {e}")
    logger.error(f"❌ Traceback: {traceback.format_exc()}")
    # ایجاد blueprint خالی برای جلوگیری از crash
    docker_bp = Blueprint('docker', __name__, url_prefix='/api/docker')
    @docker_bp.route("/error")
    def docker_error():
        return jsonify({"error": f"Module import failed: {e}"}), 500
    app.register_blueprint(docker_bp)
except Exception as e:
    logger.error(f"❌ General error during imports: {e}")
    import traceback
    logger.error(f"❌ Traceback: {traceback.format_exc()}")

@app.route("/")
def index():
    """صفحه اصلی"""
    return render_template("index.html")

@app.route("/section/<section_name>")
def get_section(section_name):
    """دریافت بخش مورد نظر"""
    try:
        return render_template(f"sections/{section_name}.html")
    except:
        return f"<div class='alert alert-danger'>بخش {section_name} یافت نشد</div>", 404

# اضافه کردن یک route برای تست ساده Docker
@app.route("/test-docker")
def test_docker():
    """تست مستقیم Docker connection"""
    try:
        import docker
        client = docker.from_env()
        client.ping()
        containers = client.containers.list(all=True)
        return f"""
        <div class='alert alert-success'>
            <h3>✅ Docker Connection Successful!</h3>
            <p>Containers: {len(containers)}</p>
            <p>First container: {containers[0].name if containers else 'None'}</p>
        </div>
        """
    except Exception as e:
        return f"""
        <div class='alert alert-danger'>
            <h3>❌ Docker Connection Failed</h3>
            <p>Error: {str(e)}</p>
            <p>User: {os.getenv('USER')}</p>
            <p>EUID: {os.geteuid()}</p>
        </div>
        """

if __name__ == "__main__":
    logger.info("Starting Flask server on 0.0.0.0:5000")
    app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)