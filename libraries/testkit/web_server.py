import json
import threading
import time
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer

from keywords.utils import log_info


class HttpHandler(BaseHTTPRequestHandler):

    server_recieved_data = []

    def do_GET(self):
        log_info('Received GET request')
        self.send_response(200)
        self.send_header('Last-Modified', self.date_time_string(time.time()))
        self.end_headers()
        self.wfile.write('Response body\n')
        return

    def do_POST(self):
        content_len = int(self.headers.getheader('content-length', 0))
        post_body = self.rfile.read(content_len)
        data = json.loads(post_body)
        HttpHandler.server_recieved_data.append(data)
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        return


class WebServer(object):
    def __init__(self, port=8080):
        self.port = port
        self.server = HTTPServer(('', port), HttpHandler)

    def start(self):
        log_info('Starting webserver on port :8080 ...')
        thread = threading.Thread(target=self.server.serve_forever)
        thread.daemon = True
        try:
            thread.start()
        except Exception as e:
            raise ValueError("Caught exception could not launch webserver thread", e)

    def stop(self):
        self.clear_data()
        self.server.shutdown()

    def clear_data(self):
        HttpHandler.server_recieved_data = []

    def get_data(self):
        return HttpHandler.server_recieved_data
