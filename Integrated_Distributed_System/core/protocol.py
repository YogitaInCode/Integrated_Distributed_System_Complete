"""Small newline-delimited JSON TCP client used by the dashboard and nodes."""
import json
import socket

NODE_HOST = "127.0.0.1"
NODE_PORTS = {1: 8101, 2: 8102, 3: 8103}


def request(node_id: int, payload: dict, timeout: float = 2.5) -> dict:
    if node_id not in NODE_PORTS:
        raise ValueError(f"Unknown node: {node_id}")
    message = (json.dumps(payload, ensure_ascii=False) + "\n").encode("utf-8")
    with socket.create_connection((NODE_HOST, NODE_PORTS[node_id]), timeout=timeout) as sock:
        sock.settimeout(timeout)
        sock.sendall(message)
        chunks = []
        while True:
            part = sock.recv(65536)
            if not part:
                break
            chunks.append(part)
            if b"\n" in part:
                break
    raw = b"".join(chunks).split(b"\n", 1)[0]
    if not raw:
        raise ConnectionError("Node closed the connection without a response.")
    return json.loads(raw.decode("utf-8"))
