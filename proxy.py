# proxy.py
from ast import Dict
import argparse, socket, threading, json
import time
from typing import Any
import LRUCache 

def pipe(src, dst,cache: LRUCache):
    """Bi-directional byte piping helper."""
    try:
        while True:
            data = src.recv(4096)
            if not data:
                break

            dst.sendall(data)
    except Exception:
        pass
    ##
    finally:
        try: dst.shutdown(socket.SHUT_WR)
        except Exception: pass


def proxy (listen_host: str, listen_port: int,server_host:str,server_port:int, cache_size: int):
    cache = LRUCache(cache_size)

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((listen_host, listen_port))
        s.listen(16)
        print(f"[proxy] listening on {listen_host}:{listen_port} -> {server_host}:{server_port} (cache={cache_size})")
        while True:
            c, addr = s.accept()
            threading.Thread(target=handle, args=(c, server_host,server_port,cache), daemon=True).start()


def main():
    ap = argparse.ArgumentParser(description="Transparent TCP proxy (optional)")
    ap.add_argument("--listen-host", default="127.0.0.1")
    ap.add_argument("--listen-port", type=int, default=5554)
    ap.add_argument("--server-host", default="127.0.0.1")
    ap.add_argument("--server-port", type=int, default=5555)
    ap.add_argument("--cache-size", type=int, default=128)
    args = ap.parse_args()
    proxy(args.listen_host, args.listen_port, args.server_host, args.server_port,args.cache_size)

   
def handle(c, sh, sp, cache: LRUCache):
    with c:    
        
       
        try:
            with socket.create_connection((sh, sp)) as s:
                t1 = threading.Thread(target=pipe, args=(c, s,cache), daemon=True)
                t2 = threading.Thread(target=pipe, args=(s, c,cache), daemon=True)
                t1.start(); t2.start()
                t1.join(); t2.join()
        except Exception as e:
            try: c.sendall((json.dumps({"ok": False, "error": f"Proxy error: {e}"})+"\n").encode("utf-8"))
            except Exception: pass
    

def handle_data(data :bytes, cache: LRUCache) -> Dict[str, Any]:
    if b"\n" in raw:
        line, _, rest = raw.partition(b"\n")
        raw = rest
        msg = json.loads(line.decode("utf-8"))

        options = msg.get("options") or {}
        use_cache = bool(options.get("cache", True))

        started = time.time()
        cache_key = json.dumps(msg, sort_keys=True)

        if use_cache:
            hit = cache.get(cache_key)
            if hit is not None:
                return {"ok": True, "result": hit, "meta": {"from_cache_proxy": True, "took_ms": int((time.time()-started)*1000)}}

    
if __name__ == "__main__":
    main()
