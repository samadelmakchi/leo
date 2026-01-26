"""
فایل اصلی Flask Application
"""

from flask import Flask, render_template

# ایمپورت ماژول‌ها
from docker_module import docker_bp
from ansible_module import ansible_bp
from cron_module import cron_bp


app = Flask(__name__)

# ثبت Blueprint ماژول‌ها
app.register_blueprint(docker_bp)
app.register_blueprint(ansible_bp)
app.register_blueprint(cron_bp)

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

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)