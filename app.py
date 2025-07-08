from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import pandas as pd
import requests
import os  # ✅ Import os to use environment variables

app = Flask(__name__)
CORS(app)

# ✅ Fetch PDFGeneratorAPI token dynamically
def get_pdfgenerator_token():
    url = "https://us1.pdfgeneratorapi.com/api/v3/auth/access-token"
    data = {
        "apiKey": os.environ.get("PDFGENERATOR_API_KEY"),
        "apiSecret": os.environ.get("PDFGENERATOR_API_SECRET")
    }
    response = requests.post(url, json=data)
    response.raise_for_status()
    return response.json()["response"]

TEMPLATE_ID = os.environ.get("PDFGENERATOR_TEMPLATE_ID")

# ✅ Load Excel data on startup
excel_file = 'Legacy data vessels.xlsx'
df = pd.read_excel(excel_file).fillna('')  # Replace NaN with empty strings
vessel_data = df.to_dict(orient='records')

@app.route('/vessels', methods=['GET'])
def get_vessels():
    return jsonify(vessel_data)

@app.route('/generate-pdf', methods=['POST'])
def generate_pdf():
    user_data = request.json

    try:
        API_TOKEN = get_pdfgenerator_token()
    except Exception as e:
        print("Error fetching PDFGeneratorAPI token:", e)
        return jsonify({"error": "Authentication failed"}), 500

    payload = {
        "name": f"Report_{user_data.get('vessel_name').replace(' ', '_')}",
        "output": "url",
        "format": "pdf",
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
            "data_suggests": user_data.get("data_suggests"),
            "we_note": user_data.get("we_note"),
            "we_suggest": user_data.get("we_suggest")
        }
    }

    headers = {
        "Authorization": f"Bearer {API_TOKEN}",
        "Content-Type": "application/json"
    }

    url = f"https://us1.pdfgeneratorapi.com/api/v3/templates/{os.environ.get('PDFGENERATOR_TEMPLATE_ID')}/output"

    response = requests.post(url, headers=headers, json=payload)

    try:
        response.raise_for_status()
        result = response.json()
        return jsonify({"pdfUrl": result.get("response")})
    except Exception as e:
        print("PDFGeneratorAPI error:", e)
        print("Response status code:", response.status_code)
        print("Response text:", response.text)
        return jsonify({"error": "PDF generation failed"}), 500

# ✅ Serve index.html from root for frontend access
@app.route('/')
def serve_index():
    return send_from_directory('.', 'index.html')

if __name__ == '__main__':
    app.run(port=5000, debug=True)
