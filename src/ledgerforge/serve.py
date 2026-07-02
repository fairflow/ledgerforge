"""Local review-tool server: static HTML + a POST-to-JSON save endpoint, hard-gated to the LAN.

Serves a directory over HTTP and accepts each page's `/save/<tool>` POST, writing it to
`save_dir/pending_<tool>.json`. Only loopback / private / link-local clients may view or save
(so `host=0.0.0.0` can share to a home wifi without exposing anything to the internet). No entity
specifics — the serve root and save dir are parameters.
"""
from __future__ import annotations

import ipaddress
import json
import socket
from datetime import datetime, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


def make_handler(serve_root, save_dir):
    serve_root, save_dir = Path(serve_root), Path(save_dir)

    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *a, **k):
            super().__init__(*a, directory=str(serve_root), **k)

        def log_message(self, fmt, *args):
            print("  " + (fmt % args), flush=True)

        def _lan_ok(self):
            try:
                ip = ipaddress.ip_address(self.client_address[0])
            except ValueError:
                return False
            return ip.is_loopback or ip.is_private or ip.is_link_local

        def do_GET(self):
            if not self._lan_ok():
                self.send_error(403, "Local network only")
                return
            super().do_GET()

        def _json(self, code, obj):
            body = json.dumps(obj).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def end_headers(self):
            self.send_header("Cache-Control", "no-store, must-revalidate")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            super().end_headers()

        def do_OPTIONS(self):
            self.send_response(204)
            self.end_headers()

        def do_POST(self):
            if not self._lan_ok():
                self.send_error(403, "Local network only")
                return
            raw = self.rfile.read(int(self.headers.get("Content-Length", 0) or 0))
            try:
                payload = json.loads(raw or b"{}")
            except Exception:
                payload = {}
            if not self.path.startswith("/save/"):
                self._json(404, {"ok": False, "error": "unknown endpoint"})
                return
            name = "".join(c for c in self.path[len("/save/"):].split("?")[0].strip("/")
                           if c.isalnum() or c in "-_") or "data"
            out = save_dir / f"pending_{name}.json"
            if name == "route_txn":
                existing = json.loads(out.read_text(encoding="utf-8")) if out.exists() else {
                    "saved_at": "", "tool": "route_txn", "payload": {"entries": []}}
                existing["payload"]["entries"].append(payload)
                existing["saved_at"] = datetime.now(timezone.utc).isoformat()
                out.write_text(json.dumps(existing, indent=2, ensure_ascii=False), encoding="utf-8")
                print(f"  route_txn appended: {payload.get('acct')} {payload.get('date')} -> {payload.get('to')}", flush=True)
                self._json(200, {"ok": True, "saved": out.name, "bytes": len(raw)})
                return
            out.write_text(json.dumps(
                {"saved_at": datetime.now(timezone.utc).isoformat(), "tool": name, "payload": payload},
                indent=2, ensure_ascii=False), encoding="utf-8")
            self._json(200, {"ok": True, "saved": out.name, "bytes": len(raw)})

    return Handler


def lan_ip() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        s.close()


def run(serve_root, save_dir, host: str = "127.0.0.1", port: int = 8765):
    Path(serve_root).mkdir(parents=True, exist_ok=True)
    srv = ThreadingHTTPServer((host, port), make_handler(serve_root, save_dir))
    print(f"ledgerforge tools server -> http://localhost:{port}/   (serving {serve_root})", flush=True)
    if host == "0.0.0.0":
        print(f"LAN access (same wifi only) -> http://{lan_ip()}:{port}/   [non-local clients get 403]", flush=True)
    print(f"saves land in {save_dir}/pending_<tool>.json", flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        srv.shutdown()
