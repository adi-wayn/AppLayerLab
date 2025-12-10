# tests/test_smoke.py
import os, sys, time, threading, socket

# מוסיפים את התיקייה הראשית ל-PYTHONPATH לפני שמייבאים server ו-client
ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, ROOT)

import server
import client


def start_server():
    # מריצים בדיוק כמו קונסול
    server.serve("127.0.0.1", 5599, 16)

def wait_for_port(host, port, timeout=3.0):
    start = time.time()
    while time.time() - start < timeout:
        try:
            with socket.create_connection((host, port), timeout=0.2):
                return
        except OSError:
            time.sleep(0.05)
    raise TimeoutError(f"Server did not open port {host}:{port} in time.")

def test_calc_and_cache():
    # Start server
    t = threading.Thread(target=start_server, daemon=True)
    t.start()

    wait_for_port("127.0.0.1", 5599)

    # פותחים חיבור כמו שהלקוח דורש
    conn = client.start_connection("127.0.0.1", 5599)

    # --- first request ---
    r1 = client.request(conn, {
        "mode": "calc",
        "data": {"expr": "sin(0)"},
        "options": {"cache": True}
    })
    assert r1["ok"] and abs(r1["result"] - 0.0) < 1e-9

    # --- second request (should come from cache) ---
    r2 = client.request(conn, {
        "mode": "calc",
        "data": {"expr": "sin(0)"},
        "options": {"cache": True}
    })
    assert r2["meta"]["from_cache"] is True

    conn.close()

if __name__ == "__main__":
    test_calc_and_cache()
    print("OK")