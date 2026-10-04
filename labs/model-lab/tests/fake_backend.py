"""Local TEST DOUBLE only. It never loads a model or uses a GPU."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import threading
import time

class FakeBackend(ThreadingHTTPServer):
    daemon_threads = True
    def __init__(self):
        self.requests = []
        self.fail_status = None
        self.slow = False
        self.drop = False
        super().__init__(('127.0.0.1', 0), Handler)
        self.thread = threading.Thread(target=self.serve_forever, daemon=True); self.thread.start()
    @property
    def base(self): return f'http://127.0.0.1:{self.server_port}/v1'
    def close(self): self.shutdown(); self.server_close(); self.thread.join(3)
class Handler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'
    def log_message(self, *args): pass
    def do_GET(self):
        data = json.dumps({'data':[{'id':'TEST_DOUBLE-not-a-real-model'}]}).encode()
        self.send_response(200); self.send_header('Content-Type','application/json'); self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
    def do_POST(self):
        data=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        self.server.requests.append(data)
        self.send_response(self.server.fail_status or 200)
        self.send_header('Content-Type','text/event-stream');self.send_header('Connection','close');self.end_headers();self.close_connection=True
        if self.server.fail_status:return
        def emit(v):
            self.wfile.write(('data: '+json.dumps(v,ensure_ascii=False)+'\n\n').encode());self.wfile.flush()
        try:
            for i,t in enumerate(['This is ', 'a local ', 'TEST DOUBLE ', 'response. ', 'Unicode: café ✓.']):
                time.sleep(.5 if self.server.slow else .02)
                emit({'choices':[{'delta':{'content':t},'finish_reason':None}]})
                if self.server.drop:return
            emit({'choices':[{'delta':{},'finish_reason':'stop'}], 'usage':{'prompt_tokens':30,'completion_tokens':12},'timings':{'predicted_per_second':25.0}})
            self.wfile.write(b'data: [DONE]\n\n');self.wfile.flush()
        except (BrokenPipeError,ConnectionResetError):pass
