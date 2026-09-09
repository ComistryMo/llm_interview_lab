"""Check the actual bundled HTTP client and native keyring using only fake data."""
import argparse
import os
from pathlib import Path
import subprocess
import tempfile


PROBE = r'''
import asyncio
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading
from uuid import uuid4
from llm_interview_lab.ai.credentials import KeyringCredentialStore
from llm_interview_lab.ai.providers import ProviderConfig, create_chat_provider
from llm_interview_lab.ai.connection_diagnostics import connection_diagnostic

class Handler(BaseHTTPRequestHandler):
    status = 401
    def log_message(self, *args): pass
    def do_POST(self):
        self.rfile.read(int(self.headers.get('Content-Length', 0)))
        self.send_response(self.status)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(b'{"choices":[{"message":{"content":"OK"}}]}')

server = HTTPServer(('127.0.0.1', 0), Handler)
thread = threading.Thread(target=server.serve_forever, daemon=True)
thread.start()
reference = None
try:
    store = KeyringCredentialStore()
    reference = store.save('release-probe-' + uuid4().hex, 'loopback', 'synthetic-local-only')
    assert store.load(reference) == 'synthetic-local-only'
    config = ProviderConfig('loopback', 'openai-compatible', 'synthetic', 'Synthetic',
                            'http://127.0.0.1:' + str(server.server_port))
    provider = create_chat_provider(config, api_key='synthetic-local-only')
    denied = asyncio.run(provider.test_connection())
    assert not denied.ok and denied.diagnostic['code'] == 'AI_CONN_AUTH_REJECTED', denied.diagnostic
    Handler.status = 200
    assert asyncio.run(provider.test_connection()).ok
    print(json.dumps({'status': 'ok', 'native_keyring': True, 'http_loopback': True, 'auth_diagnostic': True}))
except Exception as error:
    print(json.dumps(connection_diagnostic(error), ensure_ascii=False))
    raise SystemExit(1)
finally:
    if reference:
        store.delete(reference)
    server.shutdown()
    server.server_close()
'''


def check(executable: Path):
    environment = dict(os.environ)
    for name in ("PYTHONPATH", "PYTHONHOME", "PYTHON_KEYRING_BACKEND"):
        environment.pop(name, None)
    environment["NO_PROXY"] = "127.0.0.1,localhost"
    environment["PATH"] = (os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32")
                           if os.name == "nt" else "/usr/bin:/bin")
    with tempfile.TemporaryDirectory(prefix="llm-connection-probe-") as directory:
        script = Path(directory) / "probe.py"
        script.write_text(PROBE, encoding="utf-8")
        result = subprocess.run([str(executable.resolve()), "--script-worker", str(script)],
                                cwd=directory, env=environment, capture_output=True, text=True, timeout=45)
        print(result.stdout)
        if result.returncode or '"status": "ok"' not in result.stdout:
            raise RuntimeError("Packaged native keyring / loopback HTTP check failed; see sanitized diagnostic above")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("executable", type=Path)
    check(parser.parse_args().executable)
