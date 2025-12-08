# proxy.py
import argparse, socket, threading, json
from time import time
from LRUCache import LRUCache


# ---------------- Helper: read one newline-terminated message ----------------
def recv_line(sock: socket.socket, buffer: bytes):
    """
    Reads bytes from sock until one line (ending with \n) is found.
    Returns (line, updated_buffer).
    If socket closes → returns (None, buffer).
    """
    while True:
        chunk = sock.recv(4096)
        if not chunk:
            return None, buffer
        buffer += chunk
        if b"\n" in buffer:
            line, _, buffer = buffer.partition(b"\n")
            return line, buffer


# ---------------- Core: process a single JSON request ----------------
def process_request(line: bytes, server_sock: socket.socket, cache: LRUCache, server_buffer_ref):
    """
    Handles a single request:
      - Try parse JSON
      - Apply cache logic
      - Forward to server if needed
      - Receive full response line using server-buffer
    """

    started = time()

    # Try decoding JSON
    try:
        msg = json.loads(line.decode("utf-8"))
    except json.JSONDecodeError:
        # Not JSON → forward opaquely
        server_sock.sendall(line + b"\n")
        resp_line, server_buffer_ref[0] = recv_line(server_sock, server_buffer_ref[0])
        return resp_line + b"\n"

    # Close mode
    if msg.get("mode") == "close":
        server_sock.sendall(line + b"\n")
        return None

    options = msg.get("options") or {}
    use_cache = bool(options.get("cache", True))
    cache_key = json.dumps(msg, sort_keys=True)

    # ---------- CACHE HIT ----------
    if use_cache:
        hit = cache.get(cache_key)
        if hit is not None:
            took = int((time() - started) * 1000)
            resp = {
                "ok": True,
                "result": hit,
                "meta": {
                    "from_cache": True,
                    "took_ms": took
                }
            }
            return (json.dumps(resp, ensure_ascii=False) + "\n").encode("utf-8")

    # ---------- CACHE MISS ----------
    server_sock.sendall(line + b"\n")

    # Read server response (with buffer!)
    resp_line, server_buffer_ref[0] = recv_line(server_sock, server_buffer_ref[0])
    resp_bytes = resp_line + b"\n"

    # Attempt to cache only the "result"
    try:
        resp_obj = json.loads(resp_line.decode("utf-8"))
        if use_cache and resp_obj.get("ok"):
            cache.set(cache_key, resp_obj.get("result"))
    except json.JSONDecodeError:
        pass

    return resp_bytes


# ---------------- Handle one client connection ----------------
def handle(client_sock: socket.socket, server_host: str, server_port: int, cache: LRUCache):
    with client_sock:
        with socket.create_connection((server_host, server_port)) as server_sock:

            client_buffer = b""
            server_buffer = [b""]   # wrapped in list so it is mutable inside functions

            while True:
                line, client_buffer = recv_line(client_sock, client_buffer)
                if line is None:
                    break  # client closed connection

                response = process_request(line, server_sock, cache, server_buffer)

                if response is None:  # "mode: close"
                    print("[proxy] Closing connection (mode=close)")
                    break

                client_sock.sendall(response)


# ---------------- Main proxy server ----------------
def proxy(listen_host: str, listen_port: int, server_host: str, server_port: int, cache_size: int):
    cache = LRUCache(cache_size)

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((listen_host, listen_port))
        s.listen(16)

        print(f"[proxy] Listening on {listen_host}:{listen_port} → {server_host}:{server_port} (cache={cache_size})")

        while True:
            client_sock, addr = s.accept()
            print(f"[proxy] New client from {addr}")

            threading.Thread(
                target=handle,
                args=(client_sock, server_host, server_port, cache),
                daemon=True
            ).start()


def main():
    ap = argparse.ArgumentParser(description="Simple Reliable TCP Proxy with Cache")
    ap.add_argument("--listen-host", default="127.0.0.1")
    ap.add_argument("--listen-port", type=int, default=5554)
    ap.add_argument("--server-host", default="127.0.0.1")
    ap.add_argument("--server-port", type=int, default=5555)
    ap.add_argument("--cache-size", type=int, default=128)
    args = ap.parse_args()

    proxy(args.listen_host, args.listen_port, args.server_host, args.server_port, args.cache_size)


if __name__ == "__main__":
    main()