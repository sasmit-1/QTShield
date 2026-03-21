from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
from bb84_core import run_bb84
from grover_core import run_grover
from teleportation_core import run_teleportation

app = Flask(__name__)
CORS(app)

# ---- SERVE FRONTEND ----
@app.route('/')
def index():
    return render_template('index.html')

# ---- BB84 ENDPOINT ----
@app.route('/api/bb84', methods=['POST'])
def bb84():
    data       = request.get_json()
    message    = data.get('message', 'HELLO')
    eve_active = data.get('eve_active', False)
    n_bits     = data.get('n_bits', 16)
    result     = run_bb84(
        message=message,
        n_bits=n_bits,
        eve_active=eve_active
    )
    return jsonify(result)

# ---- GROVER ENDPOINT ----
@app.route('/api/grover', methods=['POST'])
def grover():
    data          = request.get_json()
    database_size = data.get('database_size', 16)
    target_index  = data.get('target_index', None)
    result        = run_grover(
        database_size=database_size,
        target_index=target_index
    )
    return jsonify(result)

# ---- TELEPORTATION ENDPOINT ----
@app.route('/api/teleport', methods=['POST'])
def teleport():
    data   = request.get_json()
    theta  = data.get('theta', None)
    phi    = data.get('phi', None)
    result = run_teleportation(
        theta=theta,
        phi=phi
    )
    return jsonify(result)

if __name__ == '__main__':
    app.run(debug=True, port=5000)