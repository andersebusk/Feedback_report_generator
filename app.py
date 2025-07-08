from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd
import requests

app = Flask(__name__)
CORS(app)

API_TOKEN = "Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiIwZDVhM2Y3YWM0OWVmNDNkODA5MTVlZGZjYjJmYzViMGRiODgzMmU1OGE3NWQyMTU3NTJiMjYwMTlkYjA2ZGE3Iiwic3ViIjoiYW5kZXJzLmJ1c2tAbWFyaW5lZmx1aWQuZGsiLCJleHAiOjE3NTE5ODE5MzJ9.HRRuY6LKD8DbWCnwhD1ZBtQVkWfTKF2S90lWYuCeJoA"
TEMPLATE_ID = "1450370"

# Load Excel data on startup
excel_file = 'Legacy data vessels.xlsx'
df = pd.read_excel(excel_file)

# Replace NaN with empty strings
df = df.fillna('')

# Convert to list of dicts
vessel_data = df.to_dict(orient='records')

@app.route('/vessels', methods=['GET'])
def get_vessels():
    return jsonify(vessel_data)

@app.route('/generate-pdf', methods=['POST'])
def generate_pdf():
    user_data = request.json

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
                "data_suggests": user_data.get("data_suggests"),
                "we_note": user_data.get("we_note"),
                "we_suggest": user_data.get("we_suggest"),
            }
        },
        "format": "pdf",
        "output": "url",
        "name": f"Report_{user_data.get('vessel_name').replace(' ', '_')}"
    }

    headers = {
        "Authorization": f"Bearer {API_TOKEN}",
        "Content-Type": "application/json"
    }

    response = requests.post("https://us1.pdfgeneratorapi.com/api/v4/documents/generate",
                             headers=headers, json=payload)

    result = response.json()
    return jsonify({"pdfUrl": result.get("response")})

if __name__ == '__main__':
    app.run(port=5000, debug=True)
