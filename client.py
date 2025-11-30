# client.py
import argparse, socket, json, sys

def start_connection(host: str, port: int) -> socket.socket:
    """Start a TCP connection to the given host and port."""
    s = socket.create_connection((host, port), timeout=5)
    print(f"[client] Connected to {host}:{port}")
    return s


def request(conn: socket.socket, payload: dict) -> dict:
    """Send a single JSON-line request and return a single JSON-line response."""
    data = (json.dumps(payload, ensure_ascii=False) + "\n").encode("utf-8")
    conn.sendall(data)

    buff = b""
    while True:
        chunk = conn.recv(4096)
        if not chunk:
            return {"ok": False, "error": "Server closed connection"}
        buff += chunk
        if b"\n" in buff:
            line, _, buff = buff.partition(b"\n")
            try:
                return json.loads(line.decode("utf-8"))
            except json.JSONDecodeError:
                return {"ok": False, "error": "Malformed JSON response"}
            
def print_menu():
    print("\n=== Client ===")
    print("Menu:")
    print("  • Type math expressions (calc mode)")
    print("  • Type gpt: <prompt> to send GPT prompt")
    print("  • Type exit/quit/close/shutdown to end the connection")
    print("  • Type 'cache off' or 'cache on' to control caching")
    print("  • Type 'help' to view the menu\n")
            
            
def run_client(host: str, port: int):
    conn = start_connection(host, port)
    use_cache = True
    print_menu()

    while True:
        user_input = input("Enter command: ").strip()

        # ---- Exit ----
        if user_input.lower() in ("exit", "close", "quit", "shutdown"):
            payload = {"mode": "close"}
            request(conn, payload)
            print("[client] Closing connection...")
            conn.close()
            break
        
        # ---- Help ----
        if user_input.lower() == "help":
            print_menu()
            continue

        # ---- Toggle cache ----
        if user_input.lower() == "cache off":
            use_cache = False
            print("[client] Cache disabled.")
            continue

        if user_input.lower() == "cache on":
            use_cache = True
            print("[client] Cache enabled.")
            continue
        
        # ---- GPT Mode ----
        if user_input.startswith("gpt: "):
            prompt = user_input[5:].strip()
            if not prompt:
                print("Prompt cannot be empty.")
                continue

            payload = {"mode": "gpt", "data": {"prompt": prompt}, "options": {"cache": use_cache}}

            resp = request(conn, payload)
            print("\n--- Response ---")
            print(json.dumps(resp, ensure_ascii=False, indent=2))
            print("----------------\n")
            continue
        
        # ---- Calc Mode ----
        else:
            expr = user_input
            if not expr:
                print("Expression cannot be empty.")
                continue

            payload = {"mode": "calc", "data": {"expr": expr}, "options": {"cache": use_cache}}

            resp = request(conn, payload)
            print("\n--- Response ---")
            print(json.dumps(resp, ensure_ascii=False, indent=2))
            print("----------------\n")


def main():
    ap = argparse.ArgumentParser(description="Client (calc/gpt over JSON TCP)")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=5555)
    args = ap.parse_args()

    run_client(args.host, args.port)

if __name__ == "__main__":
    main()