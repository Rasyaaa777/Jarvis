import os
import sys
import json
import urllib.parse
from http.server import HTTPServer, SimpleHTTPRequestHandler
import socketserver
from datetime import datetime

# Ensure project root is in sys.path
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _BASE_DIR not in sys.path:
    sys.path.insert(0, _BASE_DIR)

# Ensure UTF-8 stdout on Windows
if sys.platform == "win32":
    try:
        if sys.stdout and hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        if sys.stderr and hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from usage.tracker import get_usage_summary, get_recent_activity_logs, get_connection
from tools.reminder import set_reminder, cancel_reminder, start_reminder_daemon
from brain.router import IntentRouter

STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
_router_instance = None

def get_router():
    global _router_instance
    if _router_instance is None:
        _router_instance = IntentRouter()
    return _router_instance


class JarvisWebHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=STATIC_DIR, **kwargs)

    def _send_json(self, data, status=200):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        url = urllib.parse.urlparse(self.path)
        path = url.path

        if path == "/api/summary":
            try:
                summary = get_usage_summary()
                router = get_router()
                summary["active_provider"] = router.active_provider_name
                self._send_json(summary)
            except Exception as e:
                self._send_json({"error": str(e)}, 500)
            return

        if path == "/api/logs":
            try:
                logs = get_recent_activity_logs(limit=20)
                self._send_json({"logs": logs})
            except Exception as e:
                self._send_json({"error": str(e)}, 500)
            return

        if path == "/api/reminders":
            try:
                conn = get_connection()
                try:
                    c = conn.cursor()
                    c.execute(
                        "SELECT id, message, due_timestamp, created_at, status FROM reminders ORDER BY id DESC LIMIT 30"
                    )
                    rows = c.fetchall()
                    reminders = []
                    for r in rows:
                        reminders.append({
                            "id": r[0],
                            "message": r[1],
                            "due_timestamp": r[2],
                            "created_at": r[3],
                            "status": r[4]
                        })
                    self._send_json({"reminders": reminders})
                finally:
                    conn.close()
            except Exception as e:
                self._send_json({"error": str(e)}, 500)
            return

        # Default: Serve static index.html or assets
        if path == "/" or not os.path.exists(os.path.join(STATIC_DIR, path.lstrip("/"))):
            self.path = "/index.html"
        return super().do_GET()

    def do_POST(self):
        url = urllib.parse.urlparse(self.path)
        path = url.path

        content_length = int(self.headers.get("Content-Length", 0))
        post_data = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"
        try:
            body = json.loads(post_data)
        except Exception:
            body = {}

        if path == "/api/chat":
            message = body.get("message", "").strip()
            if not message:
                self._send_json({"error": "Empty message"}, 400)
                return
            try:
                router = get_router()
                response = router.process_messages([{"role": "user", "content": message}])
                self._send_json({"response": response})
            except Exception as e:
                self._send_json({"error": str(e)}, 500)
            return

        if path == "/api/reminders":
            msg = body.get("message", "").strip()
            delay = int(body.get("delay_seconds", 60))
            if not msg:
                self._send_json({"error": "Message is required"}, 400)
                return
            try:
                res = set_reminder(msg, delay)
                self._send_json({"result": res})
            except Exception as e:
                self._send_json({"error": str(e)}, 500)
            return

        if path == "/api/reminders/cancel":
            rem_id = str(body.get("id", "")).strip()
            if not rem_id:
                self._send_json({"error": "ID is required"}, 400)
                return
            try:
                res = cancel_reminder(rem_id)
                self._send_json({"result": res})
            except Exception as e:
                self._send_json({"error": str(e)}, 500)
            return

        if path == "/api/switch-provider":
            target = body.get("provider", "gemini").strip()
            try:
                router = get_router()
                res = router.switch_provider(target)
                self._send_json({"result": res, "active_provider": router.active_provider_name})
            except Exception as e:
                self._send_json({"error": str(e)}, 500)
            return

        self._send_json({"error": "Not Found"}, 404)


class ThreadedHTTPServer(socketserver.ThreadingMixIn, HTTPServer):
    daemon_threads = True


def start_server(port=5050):
    start_reminder_daemon()
    os.makedirs(STATIC_DIR, exist_ok=True)
    server_address = ("127.0.0.1", port)
    
    # Allow port reuse
    ThreadedHTTPServer.allow_reuse_address = True
    httpd = ThreadedHTTPServer(server_address, JarvisWebHandler)
    print(f"\n[JARVIS] Web Dashboard berjalan di: http://127.0.0.1:{port}")
    print("Tekan Ctrl+C untuk mematikan server.")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nJARVIS Web Server dihentikan.")
        httpd.server_close()


# Alias
start_web_dashboard = start_server

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5050
    start_server(port)
