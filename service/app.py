from flask import Flask, jsonify
import os
import random

app = Flask(__name__)

VERSION = os.getenv('VERSION', 'v1')
REGION = os.getenv('REGION', 'unknown')
FAILURE_RATE = float(os.getenv('FAILURE_RATE', '0.0'))  # Add this


@app.route('/')
def home():
    return jsonify({
        'status': 'running',
        'version': VERSION,
        'region': REGION
    })


@app.route('/health')
def health():
    # Simulate failures
    if random.random() < FAILURE_RATE:
        return jsonify({
            'status': 'unhealthy',
            'version': VERSION,
            'region': REGION
        }), 503

    return jsonify({
        'status': 'healthy',
        'version': VERSION,
        'region': REGION
    })


@app.route('/metrics')
def metrics():
    metrics_text = f"""# HELP service_up Service is up
# TYPE service_up gauge
service_up{{version="{VERSION}",region="{REGION}"}} 1

# HELP service_info Service information
# TYPE service_info gauge
service_info{{version="{VERSION}",region="{REGION}"}} 1
"""
    return metrics_text, 200, {'Content-Type': 'text/plain'}


if __name__ == '__main__':
    print(f"Starting service: version={VERSION}, region={REGION}, failure_rate={FAILURE_RATE}")
    app.run(host='0.0.0.0', port=8080)