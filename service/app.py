from flask import Flask, jsonify
import os

app = Flask(__name__)

# Get config from environment
VERSION = os.getenv('VERSION', 'v1')
REGION = os.getenv('REGION', 'unknown')

@app.route('/')
def home():
    return jsonify({
        'status': 'running',
        'version': VERSION,
        'region': REGION
    })

@app.route('/health')
def health():
    return jsonify({
        'status': 'healthy',
        'version': VERSION,
        'region': REGION
    })

if __name__ == '__main__':
    print(f"Starting service: version={VERSION}, region={REGION}")
    app.run(host='0.0.0.0', port=8080)