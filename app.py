from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
from flask_socketio import SocketIO, emit
from bb84_core import run_bb84, bb84_alice_prepare, bb84_eve_interfere, bb84_bob_measure
from grover_core import run_grover
from teleportation_core import run_teleportation

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# ==========================================
# SHARED STATE FOR MULTI-DEVICE BB84 DEMO
# ==========================================
bb84_state = {
    "status": "idle", # idle, alice_sent, eve_acted, bob_measured
    "message": "",
    "n_bits": 16,
    "alice_bits": [],
    "alice_bases": [],
    "quantum_circuits": [],
    "eve_disturbed": False,
    "eve_active": False,
}

# ---- SERVE FRONTEND (Monolithic) ----
@app.route('/')
def index():
    return render_template('index.html')

# ---- SERVE FRONTEND (Multi-Device Demo) ----
@app.route('/alice')
def alice_view():
    return render_template('alice.html')

@app.route('/eve')
def eve_view():
    return render_template('eve.html')

@app.route('/bob')
def bob_view():
    return render_template('bob.html')


# ---- ORIGINAL MONOLITHIC ENDPOINTS ----
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


# ==========================================
# WEBSOCKET ENDPOINTS FOR MULTI-DEVICE DEMO
# ==========================================

@socketio.on('alice_send')
def handle_alice_send(data):
    message = data.get('message', 'HELLO')
    n_bits = int(data.get('n_bits', 16))
    
    # Run Alice's preparation
    alice_bits, alice_bases, quantum_circuits, alice_bloch = bb84_alice_prepare(message, n_bits)
    
    # Store in global state
    bb84_state['status'] = 'alice_sent'
    bb84_state['message'] = message
    bb84_state['n_bits'] = n_bits
    bb84_state['alice_bits'] = alice_bits
    bb84_state['alice_bases'] = alice_bases
    bb84_state['quantum_circuits'] = quantum_circuits
    bb84_state['eve_disturbed'] = False
    bb84_state['eve_active'] = False
    
    # Broadcast that data is on the wire to all clients
    socketio.emit('data_in_transit', {
        'message': 'Qubits are in transit...',
        'n_bits': n_bits
    })

@socketio.on('eve_decision')
def handle_eve_decision(data):
    if bb84_state['status'] != 'alice_sent':
        return
    
    intercept = data.get('intercept', False)
    
    if intercept:
        # Eve intercepts
        bb84_state['eve_active'] = True
        circs, disturbed, eve_bloch = bb84_eve_interfere(
            bb84_state['quantum_circuits'],
            bb84_state['alice_bits'],
            bb84_state['alice_bases']
        )
        bb84_state['quantum_circuits'] = circs
        bb84_state['eve_disturbed'] = disturbed
        
    bb84_state['status'] = 'eve_acted'
    
    # Notify Bob that he requires to measure, and Eve that she finished
    socketio.emit('eve_acted', {'intercepted': intercept})

@socketio.on('bob_measure')
def handle_bob_measure(data):
    if bb84_state['status'] not in ['alice_sent', 'eve_acted']:
        return
        
    results = bb84_bob_measure(
        bb84_state['quantum_circuits'],
        bb84_state['alice_bits'],
        bb84_state['alice_bases'],
        bb84_state['message'],
        bb84_state['eve_disturbed'],
        bb84_state['eve_active']
    )
    
    bb84_state['status'] = 'bob_measured'
    
    # Broadcast final results to everyone (Alice, Bob, Eve)
    socketio.emit('bb84_results', results)
    
@socketio.on('reset_demo')
def handle_reset(data=None):
    bb84_state['status'] = 'idle'
    bb84_state['message'] = ""
    bb84_state['alice_bits'] = []
    bb84_state['alice_bases'] = []
    bb84_state['quantum_circuits'] = []
    bb84_state['eve_disturbed'] = False
    bb84_state['eve_active'] = False
    socketio.emit('demo_reset', {})


if __name__ == '__main__':
    # Use socketio.run instead of app.run
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)