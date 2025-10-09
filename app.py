from flask import Flask, jsonify, request, render_template, send_from_directory
from flask_cors import CORS
from datetime import datetime, timedelta
import random, math

# مسیر front-end (HTML + عکس‌ها + CSS + JS)
FRONTEND_FOLDER = r"H:\HadiSadoghiYazdi\hadisadoghiyazdi1971.github.io\hadisadoghiyazdi1971.github.io\repair-demo"

app = Flask(__name__)
CORS(app)

# --- روت برای index.html ---
@app.route('/')
def index():
    return send_from_directory(FRONTEND_FOLDER, 'index.html')

# --- روت برای سایر فایل‌های front-end (عکس‌ها، JS، CSS) ---
@app.route('/<path:path>')
def static_files(path):
    return send_from_directory(FRONTEND_FOLDER, path)

# --- روت API /optimize ---
@app.route('/optimize', methods=['POST'])
def optimize():
    try:
        data = request.get_json()
        allocation_type = data.get('allocation_type', 'random')

        # نمونه ساده پاسخ
        result = {"status": "ok", "allocation_type": allocation_type}
        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- روت HealthCheck ---
@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy"})

# اجرای سرور
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
