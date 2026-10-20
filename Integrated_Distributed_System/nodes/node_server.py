
"""A single distributed node: TCP server, SQLite replica and Lamport clock."""
from __future__ import annotations

import json
import socketserver
import sqlite3
import sys
import threading
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
PORTS = {1: 8101, 2: 8102, 3: 8103}
HOST = "127.0.0.1"


class NodeState:
    def __init__(self, node_id: int):
        self.node_id = node_id
        self.port = PORTS[node_id]
        DATA_DIR.mkdir(exist_ok=True)
        self.db_path = DATA_DIR / f"node{node_id}.db"
        self.lock = threading.RLock()
        self.clock = 0
        self._initialize()

    def connect(self):
        conn = sqlite3.connect(self.db_path, timeout=10)
        conn.row_factory = sqlite3.Row
        return conn

    def _initialize(self):
        with self.connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS students (
                    student_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    department TEXT NOT NULL,
                    version_clock INTEGER NOT NULL,
                    version_node INTEGER NOT NULL,
                    deleted INTEGER NOT NULL DEFAULT 0
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT UNIQUE,
                    node_id INTEGER NOT NULL,
                    event_type TEXT NOT NULL,
                    description TEXT NOT NULL,
                    lamport_clock INTEGER NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)
            conn.commit()

    def log(self, event_type: str, description: str, clock=None, event_id=None):
        with self.lock, self.connect() as conn:
            conn.execute(
                """INSERT OR IGNORE INTO events
                   (event_id, node_id, event_type, description, lamport_clock, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    event_id or str(uuid.uuid4()),
                    self.node_id,
                    event_type,
                    description,
                    self.clock if clock is None else clock,
                    time.strftime("%Y-%m-%d %H:%M:%S"),
                ),
            )
            conn.commit()

    def local_tick(self):
        with self.lock:
            self.clock += 1
            return self.clock

    def receive_tick(self, incoming_clock: int):
        with self.lock:
            self.clock = max(self.clock, int(incoming_clock)) + 1
            return self.clock

    def rows(self, include_deleted=False):
        with self.lock, self.connect() as conn:
            if include_deleted:
                result = conn.execute(
                    "SELECT * FROM students ORDER BY student_id"
                ).fetchall()
            else:
                result = conn.execute(
                    "SELECT * FROM students WHERE deleted=0 ORDER BY student_id"
                ).fetchall()
            return [dict(row) for row in result]

    def apply_record(self, record: dict):
        """Apply a record if its (Lamport clock, node ID) version is newer."""
        sid = str(record["student_id"]).strip()
        if not sid:
            raise ValueError("Student ID cannot be empty.")

        incoming_version = (
            int(record["version_clock"]),
            int(record["version_node"]),
        )

        with self.lock, self.connect() as conn:
            current = conn.execute(
                "SELECT version_clock, version_node FROM students WHERE student_id=?",
                (sid,),
            ).fetchone()

            if current:
                current_version = (
                    int(current["version_clock"]),
                    int(current["version_node"]),
                )
                if incoming_version <= current_version:
                    return False

            conn.execute(
                """
                INSERT INTO students
                (student_id, name, department, version_clock, version_node, deleted)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(student_id) DO UPDATE SET
                    name=excluded.name,
                    department=excluded.department,
                    version_clock=excluded.version_clock,
                    version_node=excluded.version_node,
                    deleted=excluded.deleted
                """,
                (
                    sid,
                    str(record.get("name", "")),
                    str(record.get("department", "")),
                    incoming_version[0],
                    incoming_version[1],
                    int(record.get("deleted", 0)),
                ),
            )
            conn.commit()
            return True

    def get_status(self):
        with self.lock:
            count = len(self.rows())
            return {
                "ok": True,
                "node_id": self.node_id,
                "clock": self.clock,
                "records": count,
                "port": self.port,
            }

    def get_events(self, limit=100):
        with self.lock, self.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM events ORDER BY id DESC LIMIT ?",
                (int(limit),),
            ).fetchall()
            return [dict(row) for row in rows]


class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads = True


class Handler(socketserver.StreamRequestHandler):
    def handle(self):
        try:
            line = self.rfile.readline(1024 * 1024)
            if not line:
                return

            request = json.loads(line.decode("utf-8"))
            response = self.server.state.handle_request(request)
            self.wfile.write(
                (json.dumps(response, ensure_ascii=False) + "\n").encode("utf-8")
            )
        except Exception as exc:
            error = {"ok": False, "error": str(exc)}
            try:
                self.wfile.write(
                    (json.dumps(error) + "\n").encode("utf-8")
                )
            except OSError:
                pass


def handle_request(self, request):
    action = request.get("action")

    if action == "PING":
        clock = self.local_tick()
        self.log("HEARTBEAT", "Status heartbeat received.", clock)
        return self.get_status()

    if action == "GET_STATE":
        clock = self.local_tick()
        self.log(
            "STATE_REQUEST",
            "A peer requested this node's replica state.",
            clock,
        )
        return {
            "ok": True,
            "node_id": self.node_id,
            "clock": self.clock,
            "records": self.rows(include_deleted=True),
        }

    if action == "GET_EVENTS":
        return {"ok": True, "events": self.get_events(request.get("limit", 100))}

    if action == "CLIENT_WRITE":
        if self.node_id != 1:
            return {
                "ok": False,
                "error": "Writes are coordinated by primary Node 1 in this demo.",
            }

        operation = str(request.get("operation", "")).upper()
        student_id = str(request.get("student_id", "")).strip()

        if not student_id:
            return {"ok": False, "error": "Student ID is required."}

        if operation not in ("ADD", "UPDATE", "DELETE"):
            return {"ok": False, "error": "Unsupported operation."}

        name = ""
        department = ""

        if operation in ("ADD", "UPDATE"):
            name = str(request.get("name", "")).strip()
            department = str(request.get("department", "")).strip()

            if not name or not department:
                return {
                    "ok": False,
                    "error": "Name and department are required.",
                }

        # Duplicate check and local write are protected by the node lock.
        with self.lock:

            if operation == "ADD":
                with self.connect() as conn:
                    existing = conn.execute(
                        "SELECT student_id FROM students WHERE student_id=?",
                        (student_id,),
                    ).fetchone()

                # Include deleted records to prevent reuse of an old ID.
                if existing:
                    return {
                        "ok": False,
                        "error": f"Student ID {student_id} already exists.",
                    }

            clock = self.local_tick()
            event_id = str(uuid.uuid4())

            if operation == "DELETE":
                record = {
                    "student_id": student_id,
                    "name": "",
                    "department": "",
                    "version_clock": clock,
                    "version_node": self.node_id,
                    "deleted": 1,
                }
                description = f"Deleted student {student_id}"

            else:
                record = {
                    "student_id": student_id,
                    "name": name,
                    "department": department,
                    "version_clock": clock,
                    "version_node": self.node_id,
                    "deleted": 0,
                }
                description = f"{operation.title()} student {student_id}: {name}"

            self.apply_record(record)
            self.log(operation, description, clock, event_id)

        # Replicate the successful write to both replica nodes.
        replica_results = []

        for peer_id in (2, 3):
            try:
                ack = send_to_node(
                    peer_id,
                    {
                        "action": "REPLICATE",
                        "record": record,
                        "event_id": event_id,
                        "sender_clock": clock,
                        "description": description,
                    },
                )

                replica_results.append({
                    "node_id": peer_id,
                    "ok": ack.get("ok", False),
                    "message": ack.get("message", ack.get("error", "")),
                })

            except Exception as exc:
                replica_results.append({
                    "node_id": peer_id,
                    "ok": False,
                    "message": str(exc),
                })

        return {
            "ok": True,
            "event_id": event_id,
            "clock": clock,
            "record": record,
            "replicas": replica_results,
        }

    if action == "REPLICATE":
        incoming = int(request.get("sender_clock", 0))
        clock = self.receive_tick(incoming)
        record = request["record"]
        changed = self.apply_record(record)

        event_id = f"{request.get('event_id')}-at-node-{self.node_id}"
        description = request.get("description", "Replica update")

        self.log(
            "REPLICATION",
            description + (" (applied)" if changed else " (already current)"),
            clock,
            event_id,
        )

        return {
            "ok": True,
            "message": "Replica updated" if changed else "Replica already current",
            "clock": clock,
            "changed": changed,
        }

    if action == "SYNC_APPLY":
        sender_clock = int(request.get("sender_clock", 0))
        clock = self.receive_tick(sender_clock)
        changed = self.apply_record(request["record"])

        self.log(
            "RECOVERY",
            f"Recovery synchronization for {request['record']['student_id']}",
            clock,
        )

        return {"ok": True, "changed": changed, "clock": clock}

    return {"ok": False, "error": f"Unknown action: {action}"}


def send_to_node(node_id, payload):
    import socket

    data = (json.dumps(payload, ensure_ascii=False) + "\n").encode("utf-8")

    with socket.create_connection(
        (HOST, PORTS[node_id]), timeout=2.0
    ) as sock:
        sock.settimeout(3.0)
        sock.sendall(data)
        file = sock.makefile("rb")
        line = file.readline()

    if not line:
        raise ConnectionError("Peer returned an empty response.")

    return json.loads(line.decode("utf-8"))


def main():
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python nodes/node_server.py <1|2|3>")

    node_id = int(sys.argv[1])

    if node_id not in PORTS:
        raise SystemExit("Node ID must be 1, 2, or 3.")

    state = NodeState(node_id)
    state.handle_request = handle_request.__get__(state, NodeState)

    server = ThreadedTCPServer((HOST, PORTS[node_id]), Handler)
    server.state = state

    print(
        f"Node {node_id} listening on {HOST}:{PORTS[node_id]}",
        flush=True,
    )

    try:
        server.serve_forever(poll_interval=0.3)
    except KeyboardInterrupt:
        print(f"Node {node_id} shutting down.", flush=True)
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
