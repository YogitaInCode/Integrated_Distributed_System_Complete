# Integrated Distributed System
### Communication • Lamport Logical Clocks • Data Replication • Failure Detection • Recovery

A local, three-node distributed-system demonstration built with Python TCP sockets, SQLite and Streamlit.

## Features
- Three independent node processes with separate SQLite databases.
- TCP request/response communication using newline-delimited JSON.
- Lamport logical clocks: local events increment the clock; received messages use `max(local, received) + 1`.
- Student-record create, update and delete operations.
- Primary-node write flow (Node 1) with replication to Nodes 2 and 3.
- Idempotent replication using unique event IDs.
- Heartbeat-based node status display.
- Manual recovery/synchronization for a node that was offline.
- Dashboard for records, node status, logical clocks, event logs and replication results.
- Demo controls for stopping/restarting an individual node.

## Requirements
- Windows 10/11, macOS or Linux
- Python 3.9+
- VS Code

No external database server is needed. Each node stores its own SQLite database in `data/`.

## Setup in VS Code

1. Extract the ZIP file.
2. Open the extracted `Integrated_Distributed_System` folder in VS Code.
3. Open Terminal → New Terminal.
4. Create a virtual environment (recommended):

   **Windows PowerShell**
   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

   If PowerShell blocks activation, run:
   ```powershell
   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
   .\.venv\Scripts\Activate.ps1
   ```

   **macOS/Linux**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

5. Install dependencies:
   ```bash
   python -m pip install -r requirements.txt
   ```

## Run the application

From the project root folder:

```bash
python -m streamlit run app.py
```

A browser tab should open at `http://localhost:8501`.

1. In the sidebar, click **Start all nodes**.
2. Wait until the three node cards show **ONLINE**.
3. Add a student record using the form.
4. Watch the operation timestamp and replication acknowledgements.
5. Open the **Logical clocks & events** section to inspect each node's clock and event history.
6. Use **Stop Node 2** to simulate a failure. Add another record while Node 2 is offline. Restart Node 2, then click **Synchronize selected node** to recover missed records.

The app can also be started using:
```bash
streamlit run app.py
```

## Default local node addresses
- Node 1: `127.0.0.1:8101` (primary/write coordinator)
- Node 2: `127.0.0.1:8102`
- Node 3: `127.0.0.1:8103`

Only use these nodes on your own machine for this classroom demo. The sample server binds to localhost and is not configured for public network exposure or production security.

## Lamport clock rule implemented

For a local event:
```text
L = L + 1
```

When a message carrying timestamp `T` is received:
```text
L = max(L, T) + 1
```

The logical clock establishes a consistent ordering for causally related events. It is not a physical clock and does not guarantee that every pair of concurrent events can be ordered by causality alone.

## Project structure

```text
Integrated_Distributed_System/
├── app.py
├── requirements.txt
├── README.md
├── start_nodes.bat
├── stop_nodes.bat
├── nodes/
│   ├── __init__.py
│   └── node_server.py
├── core/
│   ├── __init__.py
│   ├── protocol.py
│   └── node_manager.py
├── data/                 # node databases are created here on first run
└── logs/                 # node process logs are created here
```

## Troubleshooting

- **Node shows OFFLINE:** click Start all nodes again and inspect `logs/node1.log`, `logs/node2.log` or `logs/node3.log`.
- **Port already in use:** stop any earlier copy of this project or change the port constants in `core/protocol.py` and `core/node_manager.py`.
- **Streamlit command not found:** use `python -m streamlit run app.py`.
- **PowerShell activation blocked:** use the process-scoped execution-policy command shown above.
- **A node was offline during writes:** restart it and use the recovery/synchronization control. Replication to an offline node is expected to fail until recovery.

## Academic note
This is an educational prototype, not a production consensus system. Node 1 acts as the primary for user writes. Replication acknowledgements are shown per node; if a replica is offline, the dashboard reports partial replication rather than claiming all replicas committed.
