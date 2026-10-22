from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import os
from pathlib import Path
class Handler(BaseHTTPRequestHandler):
 def do_GET(self):
  if self.path in ('/','/index.html'):
   body=(Path(__file__).parent/'index.html').read_bytes();code=200;kind='text/html; charset=utf-8'
  elif self.path=='/healthz':body=b'ok';code=200;kind='text/plain'
  else:body=b'not found';code=404;kind='text/plain'
  self.send_response(code);self.send_header('Content-Type',kind);self.send_header('Content-Length',str(len(body)));self.send_header('X-Content-Type-Options','nosniff');self.end_headers();self.wfile.write(body)
if __name__=='__main__':ThreadingHTTPServer(('0.0.0.0',int(os.environ.get('PORT','10000'))),Handler).serve_forever()
