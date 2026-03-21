import random
import math
from qiskit import QuantumCircuit, transpile
from qiskit_aer import Aer
from qiskit.quantum_info import Statevector

# ============================================
# HELPER: Get Bloch Sphere Coordinates
# ============================================
def get_bloch_coords(qc):
    """
    Takes a quantum circuit and returns
    the x, y, z position on the Bloch sphere.
    Member 3 uses these to animate the sphere.
    """
    state = Statevector(qc)
    a = state[0]  # amplitude of |0>
    b = state[1]  # amplitude of |1>

    x = float(2 * (a.real * b.real + a.imag * b.imag))
    y = float(2 * (a.real * b.imag - a.imag * b.real))
    z = float(a.real**2 + a.imag**2 - b.real**2 - b.imag**2)

    return {"x": round(x, 4), 
            "y": round(y, 4), 
            "z": round(z, 4)}


# ============================================
# HELPER: Prepare Alice's Qubit
# ============================================
def prepare_qubit(bit, basis):
    """
    Alice prepares a qubit.
    bit   = 0 or 1
    basis = '+' (straight) or 'x' (diagonal)
    
    Returns the quantum circuit AND
    its Bloch sphere coordinates.
    """
    qc = QuantumCircuit(1)

    # Step 1: Encode the bit
    if bit == 1:
        qc.x(0)  # Flip qubit to |1>

    # Step 2: Apply basis
    if basis == 'x':
        qc.h(0)  # Hadamard gate = diagonal basis

    # Get Bloch coordinates BEFORE measurement
    bloch = get_bloch_coords(qc)

    return qc, bloch


# ============================================
# HELPER: Bob Measures the Qubit
# ============================================
def measure_qubit(qc, basis):
    """
    Bob measures the qubit.
    If his basis matches Alice's, he gets
    the correct bit. Otherwise random.
    """
    # Add classical bit for measurement result
    qc.add_register(__import__('qiskit').ClassicalRegister(1))

    if basis == 'x':
        qc.h(0)  # Rotate back before measuring

    qc.measure(0, 0)

    # Run on Aer simulator
    simulator = Aer.get_backend('aer_simulator')
    compiled = transpile(qc, simulator)
    job = simulator.run(compiled, shots=1)
    result = job.result()
    counts = result.get_counts()

    # Get the measured bit
    measured_bit = int(list(counts.keys())[0])
    return measured_bit


# ============================================
# HELPER: Eve Intercepts
# ============================================
def eve_intercept(alice_bit, alice_basis):
    """
    Fully quantum Eve interception using Qiskit.
    Eve measures in a random basis using a real
    quantum circuit — not random.randint().
    """
    eve_basis = random.choice(['+', 'x'])
    
    # Step 1: Recreate Alice's qubit as a quantum circuit
    qc = QuantumCircuit(1, 1)
    if alice_bit == 1:
        qc.x(0)
    if alice_basis == 'x':
        qc.h(0)
    
    # Step 2: Eve measures in HER basis (quantum measurement)
    if eve_basis == 'x':
        qc.h(0)  # Rotate to Eve's basis
    qc.measure(0, 0)
    
    # Step 3: Run on Qiskit Aer — REAL quantum simulation
    simulator = Aer.get_backend('aer_simulator')
    compiled  = transpile(qc, simulator)
    job       = simulator.run(compiled, shots=1)
    result    = job.result()
    counts    = result.get_counts()
    
    # Step 4: Eve reads her measurement result
    eve_bit = int(list(counts.keys())[0])
    
    # Step 5: Eve re-prepares and sends her version
    # This is the disturbance — she cannot send
    # the original because she destroyed it by measuring
    new_qc = QuantumCircuit(1)
    if eve_bit == 1:
        new_qc.x(0)
    if eve_basis == 'x':
        new_qc.h(0)
    
    # Was the qubit disturbed?
    disturbed = eve_basis != alice_basis
    
    return new_qc, disturbed

# ============================================
# HELPER: Encrypt Message with Quantum Key
# ============================================
def encrypt_message(message, key):
    """
    Encrypts a text message using the
    quantum-generated key as a one-time pad.
    XOR each bit of the message with the key.
    """
    # Convert message to binary
    message_bits = []
    for char in message:
        bits = format(ord(char), '08b')
        message_bits.extend([int(b) for b in bits])

    # Extend key to match message length
    extended_key = []
    while len(extended_key) < len(message_bits):
        extended_key.extend(key)
    extended_key = extended_key[:len(message_bits)]

    # XOR encryption
    encrypted_bits = [m ^ k for m, k 
                      in zip(message_bits, extended_key)]

    return encrypted_bits, extended_key


# ============================================
# HELPER: Decrypt Message
# ============================================
def decrypt_message(encrypted_bits, key):
    """
    Decrypts using the same quantum key.
    XOR is its own inverse — XOR again to decrypt.
    """
    extended_key = []
    while len(extended_key) < len(encrypted_bits):
        extended_key.extend(key)
    extended_key = extended_key[:len(encrypted_bits)]

    # XOR decryption
    decrypted_bits = [e ^ k for e, k 
                      in zip(encrypted_bits, extended_key)]

    # Convert binary back to text
    chars = []
    for i in range(0, len(decrypted_bits), 8):
        byte = decrypted_bits[i:i+8]
        if len(byte) == 8:
            char = chr(int(''.join(map(str, byte)), 2))
            chars.append(char)

    return ''.join(chars)


# ============================================
# MAIN FUNCTION: Run Full BB84 Protocol
# ============================================
def run_bb84(message="HELLO", n_bits=16, eve_active=False):
    """
    Runs the complete BB84 protocol.
    
    Parameters:
        message    : text to encrypt with quantum key
        n_bits     : number of qubits to send
        eve_active : whether Eve intercepts
    
    Returns:
        Complete results dict for Member 2 (Flask API)
        and Member 3/4 (frontend visualisation)
    """

    alice_bits   = []
    alice_bases  = []
    bob_bases    = []
    bob_bits     = []
    bloch_states = []  # For Bloch sphere animation

    for i in range(n_bits):
        # Alice randomly picks a bit and basis
        bit   = random.randint(0, 1)
        basis = random.choice(['+', 'x'])

        alice_bits.append(bit)
        alice_bases.append(basis)

        # Alice prepares the qubit
        qc, bloch = prepare_qubit(bit, basis)
        bloch_states.append({
            "step":  i,
            "owner": "alice",
            "state": bloch
        })

        # Eve intercepts if active
        if eve_active:
            qc, disturbed = eve_intercept(bit, basis)
            bloch_states.append({
                "step":     i,
                "owner":    "eve",
                "disturbed": disturbed,
                "state":    get_bloch_coords(qc)
            })

        # Bob randomly picks a basis and measures
        bob_basis = random.choice(['+', 'x'])
        bob_bases.append(bob_basis)
        bob_bit = measure_qubit(qc, bob_basis)
        bob_bits.append(bob_bit)

        bloch_states.append({
            "step":  i,
            "owner": "bob",
            "state": {"x": 0, "y": 0, 
                      "z": 1 if bob_bit == 0 else -1}
        })

    # ---- SIFTING ----
    # Keep only bits where bases matched
    matches = []
    final_key = []

    for i in range(n_bits):
        match = alice_bases[i] == bob_bases[i]
        matches.append(match)
        if match:
            final_key.append(alice_bits[i])

    # ---- ERROR RATE ----
    # Check errors on matching bits
    errors = 0
    matching_count = 0

    for i in range(n_bits):
        if matches[i]:
            matching_count += 1
            if alice_bits[i] != bob_bits[i]:
                errors += 1

    error_rate = round(
        errors / max(matching_count, 1), 4
    )
    eve_detected = error_rate > 0.1

    # ---- MESSAGE ENCRYPTION ----
    if eve_detected:
        # Key is compromised — throw everything away
        # This is the entire point of BB84
        encrypted_bits    = []
        encrypted_display = "TRANSMISSION ABORTED"
        decrypted_message = "⚠️ EVE DETECTED — Key discarded. Message never sent."

    elif len(final_key) > 0:
        # Key is clean — safe to encrypt
        encrypted_bits, used_key = encrypt_message(
            message, final_key
        )
        decrypted_message = decrypt_message(
            encrypted_bits, final_key
        )
        encrypted_display = ''.join(
            map(str, encrypted_bits[:32])
        ) + "..."
    else:
        encrypted_bits    = []
        encrypted_display = "Key too short"
        decrypted_message = "Not enough matching bits"

    # ---- RETURN EVERYTHING ----
    return {
        "alice_bits":          alice_bits,
        "alice_bases":         alice_bases,
        "bob_bases":           bob_bases,
        "bob_bits":            bob_bits,
        "matches":             matches,
        "final_key":           final_key,
        "error_rate":          error_rate,
        "eve_active":          eve_active,
        "eve_detected":        eve_detected,
        "original_message":    message,
        "encrypted_display":   encrypted_display,
        "decrypted_message":   decrypted_message,
        "bloch_states":        bloch_states,
        "key_length":          len(final_key),
        "matching_bits":       matching_count
    }


# ============================================
# TEST IT — Run this to verify everything works
# ============================================
if __name__ == "__main__":

    print("=" * 50)
    print("TEST 1: No Eve")
    print("=" * 50)
    result = run_bb84(
        message="HELLO", 
        n_bits=16, 
        eve_active=False
    )
    print(f"Error Rate:         {result['error_rate']}")
    print(f"Eve Detected:       {result['eve_detected']}")
    print(f"Final Key:          {result['final_key']}")
    print(f"Key Length:         {result['key_length']}")
    print(f"Original Message:   {result['original_message']}")
    print(f"Encrypted (first32):{result['encrypted_display']}")
    print(f"Decrypted Message:  {result['decrypted_message']}")

    print()
    print("=" * 50)
    print("TEST 2: Eve Active")
    print("=" * 50)
    result2 = run_bb84(
        message="HELLO", 
        n_bits=16, 
        eve_active=True
    )
    print(f"Error Rate:         {result2['error_rate']}")
    print(f"Eve Detected:       {result2['eve_detected']}")
    print(f"Key Length:         {result2['key_length']}")
    print(f"Decrypted Message:  {result2['decrypted_message']}")

    print()
    print("=" * 50)
    print("TEST 3: Bloch States Sample")
    print("=" * 50)
    for state in result['bloch_states'][:3]:
        print(state)