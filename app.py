from flask import Flask, request, jsonify, send_from_directory, Response
from flask_cors import CORS
import pandas as pd
import requests
import os
import jwt
import time
from functools import wraps
from datetime import datetime, timezone
import boto3

app = Flask(__name__)
CORS(app)

# 🔑 Basic Auth setup
USERNAME = os.environ.get("APP_USERNAME", "defaultusername")
PASSWORD = os.environ.get("APP_PASSWORD", "defaultpassword")

def check_auth(username, password):
    return username == USERNAME and password == PASSWORD

def authenticate():
    return Response(
        'Could not verify your access.\n'
        'You need to login with proper credentials.', 401,
        {'WWW-Authenticate': 'Basic realm="Login Required"'}
    )

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated

# 🔑 JWT generation for PDFGeneratorAPI
def get_pdfgenerator_jwt():
    API_KEY = os.environ.get("PDFGENERATOR_API_KEY")
    API_SECRET = os.environ.get("PDFGENERATOR_API_SECRET")
    WORKSPACE_IDENTIFIER = os.environ.get("PDFGENERATOR_WORKSPACE_IDENTIFIER")

    payload = {
        "iss": API_KEY,
        "sub": WORKSPACE_IDENTIFIER,
        "exp": int(time.time()) + 60  # valid 60 seconds
    }

    token = jwt.encode(payload, API_SECRET, algorithm="HS256")
    return token

TEMPLATE_ID = os.environ.get("PDFGENERATOR_TEMPLATE_ID")

# ✅ Load Excel data on startup
excel_file = 'Legacy data vessels.xlsx'
df = pd.read_excel(excel_file).fillna('')
vessel_data = df.to_dict(orient='records')

# 🔷 S3 client setup
BUCKET_NAME = 'feedbackreportimages'

s3_client = boto3.client(
    's3',
    region_name="eu-north-1",
    aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY")
)

@app.route('/upload-image', methods=['POST'])
@requires_auth
def upload_image():
    file = request.files['image']

    if not file:
        return jsonify({'error': 'No file provided'}), 400

    try:
        timestamp = datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')
        filename = f"{timestamp}_{file.filename}"
        print("Uploading to S3:", filename)

        s3_client.upload_fileobj(file, BUCKET_NAME, filename, ExtraArgs={'ContentType': file.content_type})

        presigned_url = s3_client.generate_presigned_url('get_object',
            Params={'Bucket': BUCKET_NAME, 'Key': filename},
            ExpiresIn=604800)

        print("Generated presigned URL:", presigned_url)
        return jsonify({'url': presigned_url})

    except Exception as e:
        print("S3 upload error:", e)
        return jsonify({'error': 'Upload failed'}), 500

@app.route('/vessels', methods=['GET'])
@requires_auth
def get_vessels():
    return jsonify(vessel_data)

@app.route('/generate-pdf', methods=['POST'])
@requires_auth
def generate_pdf():
    today_str = datetime.today().strftime('%Y-%m-%d')
    user_data = request.json

    print("Received user data:", user_data)  # 🔷 Debug user data

    try:
        API_TOKEN = get_pdfgenerator_jwt()
        print("Generated PDFGeneratorAPI JWT")
    except Exception as e:
        print("Error generating JWT token:", e)
        return jsonify({"error": "Authentication failed"}), 500

    payload = {
        "template": {
            "id": TEMPLATE_ID,
            "data": {
                "customer": user_data.get("customer"),
                "vessel_name": user_data.get("vessel_name"),
                "date": user_data.get("date"),
                "eng_name": user_data.get("eng_name"),
                "imo_no": user_data.get("imo_no"),
                "status": user_data.get("status"),
                "en_manu": user_data.get("en_manu"),
                "en_mod": user_data.get("en_mod"),
                "sample_per": user_data.get("sample_per"),
                "on_sample_date": user_data.get("on_sample_date"),
                "lab_sample_date": user_data.get("lab_sample_date"),
                "avg_load": user_data.get("avg_load"),
                "fo_sulph": user_data.get("fo_sulph"),
                "fil_pur": user_data.get("fil_pur"),
                "clo_bn": user_data.get("clo_bn"),
                "clo_24hrs": user_data.get("clo_24hrs"),
                "acc_fac": user_data.get("acc_fac"),
                "feed_before": user_data.get("feed_before"),
                "feed_rep": user_data.get("feed_rep"),
                "res_bn_obs": user_data.get("res_bn_obs"),
                "fe_tot_obs": user_data.get("fe_tot_obs"),
                "feed_obs": user_data.get("feed_obs"),
                "add_com_obs": user_data.get("add_com_obs"),
                "we_suggest": user_data.get("we_suggest"),
                "add_com_sugg": user_data.get("add_com_sugg"),
                "fe_tbn_image_url": user_data.get("fe_tbn_image_url"),
                "tbn_fed_image_url": user_data.get("tbn_fed_image_url"),
                "fe_tot_load_image_url": user_data.get("fe_tot_load_image_url"),
                "feedrate_load_fe_image_url": user_data.get("feedrate_load_fe_image_url"),
            }
        },
        "format": "pdf",
        "output": "url",
        "name": f"{today_str}_Report_{user_data.get('vessel_name').replace(' ', '_')}"
    }

    print("Payload for PDFGeneratorAPI:", payload)  # 🔷 Debug payload

    headers = {
        "Authorization": f"Bearer {API_TOKEN}",
        "Content-Type": "application/json"
    }

    url = "https://us1.pdfgeneratorapi.com/api/v4/documents/generate"

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        result = response.json()
        print("PDF generated successfully. URL:", result.get("response"))
        return jsonify({"pdfUrl": result.get("response")})
    except Exception as e:
        print("PDFGeneratorAPI error:", e)
        print("Response status code:", response.status_code)
        print("Response text:", response.text)
        return jsonify({"error": "PDF generation failed"}), 500

@app.route('/')
@requires_auth
def serve_index():
    return send_from_directory('.', 'index.html')

if __name__ == '__main__':
    app.run(port=5000, debug=True)
