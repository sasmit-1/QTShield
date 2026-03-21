import numpy as np
from qiskit import QuantumCircuit, transpile
from qiskit_aer import Aer
from qiskit.quantum_info import Statevector

# ============================================
# HELPER: Build the Oracle
# The Oracle marks the target item by
# flipping its amplitude from + to -
# This is the "I found it" signal
# ============================================
def build_oracle(n_qubits, target_index):
    """
    Marks the target item in the database.
    Target is identified by its index.
    
    Example: database of 4 items (2 qubits)
    target_index=2 marks item |10>
    """
    oracle = QuantumCircuit(n_qubits)
    
    # Convert target index to binary
    target_binary = format(
        target_index, f'0{n_qubits}b'
    )
    
    # Flip qubits that are 0 in target
    # This sets up the controlled-Z gate
    for i, bit in enumerate(reversed(target_binary)):
        if bit == '0':
            oracle.x(i)
    
    # Apply multi-controlled Z gate
    # This flips the phase of the target state
    if n_qubits == 1:
        oracle.z(0)
    else:
        oracle.h(n_qubits - 1)
        oracle.mcx(
            list(range(n_qubits - 1)), 
            n_qubits - 1
        )
        oracle.h(n_qubits - 1)
    
    # Unflip the qubits we flipped earlier
    for i, bit in enumerate(reversed(target_binary)):
        if bit == '0':
            oracle.x(i)
    
    return oracle


# ============================================
# HELPER: Build the Diffuser
# The Diffuser amplifies the marked item
# and suppresses everything else
# This is the "push probability toward target"
# ============================================
def build_diffuser(n_qubits):
    """
    Grover's diffusion operator.
    Amplifies the target amplitude.
    Think of it as tilting a table so
    the marble rolls toward the target.
    """
    diffuser = QuantumCircuit(n_qubits)
    
    # Apply Hadamard to all qubits
    diffuser.h(range(n_qubits))
    
    # Apply X to all qubits
    diffuser.x(range(n_qubits))
    
    # Apply multi-controlled Z
    if n_qubits == 1:
        diffuser.z(0)
    else:
        diffuser.h(n_qubits - 1)
        diffuser.mcx(
            list(range(n_qubits - 1)),
            n_qubits - 1
        )
        diffuser.h(n_qubits - 1)
    
    # Unflip
    diffuser.x(range(n_qubits))
    diffuser.h(range(n_qubits))
    
    return diffuser


# ============================================
# HELPER: Get Amplitudes After Each Iteration
# This is what Member 3 uses to animate
# the database grid getting brighter
# ============================================
def get_amplitudes(qc, n_qubits):
    """
    Returns the probability of each item
    in the database after current circuit state.
    Higher probability = brighter box in UI.
    """
    state = Statevector(qc)
    probabilities = np.abs(state.data) ** 2
    
    return [
        {
            "index": i,
            "probability": round(float(p), 6),
            "amplitude": round(
                float(np.abs(state.data[i])), 6
            )
        }
        for i, p in enumerate(probabilities)
    ]


# ============================================
# HELPER: Classical Search Simulation
# For the side-by-side comparison
# Shows how slow classical search is
# ============================================
def classical_search(database_size, target_index):
    """
    Simulates classical linear search.
    Checks items one by one until found.
    Returns steps taken and the path.
    """
    steps = []
    for i in range(database_size):
        steps.append({
            "step": i + 1,
            "checking_index": i,
            "found": i == target_index
        })
        if i == target_index:
            break
    
    return {
        "steps_taken": len(steps),
        "path": steps,
        "worst_case": database_size,
        "average_case": database_size // 2
    }


# ============================================
# MAIN FUNCTION: Run Grover's Algorithm
# ============================================
def run_grover(database_size=16, target_index=None):
    """
    Runs Grover's search algorithm.
    
    Parameters:
        database_size : must be power of 2
                        (4, 8, 16, 32)
        target_index  : which item to find
                        if None, picks randomly
    
    Returns:
        Complete results for Flask API
        and frontend animation
    """
    
    # Validate database size is power of 2
    if database_size not in [4, 8, 16, 32, 64]:
        database_size = 16
    
    # Calculate number of qubits needed
    n_qubits = int(np.log2(database_size))
    
    # Pick random target if not specified
    if target_index is None:
        import random
        target_index = random.randint(
            0, database_size - 1
        )
    
    # Clamp target to valid range
    target_index = target_index % database_size
    
    # Calculate optimal number of iterations
    # This is the mathematical sweet spot
    # Too few = not enough amplification
    # Too many = amplification reverses
    optimal_iterations = max(
        1, int(np.pi / 4 * np.sqrt(database_size))
    )
    
    # ---- BUILD THE CIRCUIT ----
    qc = QuantumCircuit(n_qubits)
    
    # Step 1: Put all qubits in superposition
    # All items equally likely at this point
    qc.h(range(n_qubits))
    
    # Get initial amplitudes (all equal)
    initial_amplitudes = get_amplitudes(qc, n_qubits)
    
    # ---- RUN GROVER ITERATIONS ----
    iteration_data = []
    
    # Save state after superposition
    iteration_data.append({
        "iteration": 0,
        "label": "Initial Superposition",
        "amplitudes": initial_amplitudes,
        "description": "All items equally likely"
    })
    
    oracle  = build_oracle(n_qubits, target_index)
    diffuser = build_diffuser(n_qubits)
    
    for i in range(optimal_iterations):
        # Apply Oracle — marks the target
        qc.compose(oracle, inplace=True)
        
        # Apply Diffuser — amplifies target
        qc.compose(diffuser, inplace=True)
        
        # Get amplitudes after this iteration
        amplitudes = get_amplitudes(qc, n_qubits)
        
        # Find current highest probability item
        best = max(
            amplitudes, 
            key=lambda x: x["probability"]
        )
        
        iteration_data.append({
            "iteration": i + 1,
            "label": f"After Iteration {i + 1}",
            "amplitudes": amplitudes,
            "current_best_index": best["index"],
            "target_probability": round(
                amplitudes[target_index]["probability"],
                4
            ),
            "description": (
                f"Target probability: "
                f"{amplitudes[target_index]['probability']:.1%}"
            )
        })
    
    # ---- MEASURE THE RESULT ----
    qc.measure_all()
    
    simulator = Aer.get_backend('aer_simulator')
    compiled  = transpile(qc, simulator)
    job       = simulator.run(compiled, shots=1000)
    result    = job.result()
    counts    = result.get_counts()
    
    # Find most measured result
    most_likely = max(counts, key=counts.get)
    measured_index = int(most_likely, 2)
    success = measured_index == target_index
    
    # ---- CLASSICAL COMPARISON ----
    classical = classical_search(
        database_size, target_index
    )
    
    # ---- SPEEDUP CALCULATION ----
    quantum_steps  = optimal_iterations
    classical_steps = classical["steps_taken"]
    speedup = round(
        classical_steps / max(quantum_steps, 1), 2
    )
    
    # ---- REAL WORLD NUMBERS ----
    # At 1 billion items (drug discovery scale)
    billion_classical = 1_000_000_000
    billion_quantum   = int(
        np.pi / 4 * np.sqrt(billion_classical)
    )
    
    return {
        # Core results
        "database_size":      database_size,
        "n_qubits":           n_qubits,
        "target_index":       target_index,
        "measured_index":     measured_index,
        "success":            success,
        
        # Iteration animation data
        # Member 3 uses this to animate
        # each box getting brighter
        "iterations":         iteration_data,
        "optimal_iterations": optimal_iterations,
        
        # Classical vs Quantum comparison
        "quantum_steps":      quantum_steps,
        "classical_steps":    classical_steps,
        "speedup":            speedup,
        "classical_path":     classical["path"],
        
        # Measurement statistics
        "measurement_counts": dict(sorted(
            counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:8]),
        
        # Real world context
        "real_world": {
            "scenario": "Pharmaceutical compound search",
            "billion_item_classical_steps": 
                billion_classical,
            "billion_item_quantum_steps":   
                billion_quantum,
            "billion_speedup": round(
                billion_classical / billion_quantum, 0
            )
        }
    }


# ============================================
# TEST IT
# ============================================
if __name__ == "__main__":
    
    print("=" * 50)
    print("TEST 1: 16 item database")
    print("=" * 50)
    result = run_grover(
        database_size=16,
        target_index=7
    )
    print(f"Database Size:      {result['database_size']}")
    print(f"Target Index:       {result['target_index']}")
    print(f"Measured Index:     {result['measured_index']}")
    print(f"Success:            {result['success']}")
    print(f"Quantum Steps:      {result['quantum_steps']}")
    print(f"Classical Steps:    {result['classical_steps']}")
    print(f"Speedup:            {result['speedup']}x faster")
    
    print()
    print("=" * 50)
    print("TEST 2: 32 item database")
    print("=" * 50)
    result2 = run_grover(
        database_size=32,
        target_index=15
    )
    print(f"Database Size:      {result2['database_size']}")
    print(f"Target Index:       {result2['target_index']}")
    print(f"Measured Index:     {result2['measured_index']}")
    print(f"Success:            {result2['success']}")
    print(f"Quantum Steps:      {result2['quantum_steps']}")
    print(f"Classical Steps:    {result2['classical_steps']}")
    print(f"Speedup:            {result2['speedup']}x faster")
    
    print()
    print("=" * 50)
    print("TEST 3: Real World Numbers")
    print("=" * 50)
    rw = result['real_world']
    print(f"Scenario:           {rw['scenario']}")
    print(f"Classical Steps:    "
          f"{rw['billion_item_classical_steps']:,}")
    print(f"Quantum Steps:      "
          f"{rw['billion_item_quantum_steps']:,}")
    print(f"Speedup:            "
          f"{rw['billion_speedup']:,.0f}x faster")
    
    print()
    print("=" * 50)
    print("TEST 4: Iteration Animation Data")
    print("=" * 50)
    for iteration in result['iterations']:
        target_prob = iteration['amplitudes'][
            result['target_index']
        ]['probability']
        print(
            f"Iteration {iteration['iteration']}: "
            f"Target probability = {target_prob:.1%}"
        )