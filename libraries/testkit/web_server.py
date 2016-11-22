from BaseHTTPServer import BaseHTTPRequestHandler
import time
import json
from BaseHTTPServer import HTTPServer
import threading
from libraries.testkit import settings
import logging
log = logging.getLogger(settings.LOGGER)


server_received_data = []


class HttpHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        log.info('Received GET request')
        self.send_response(200)
        self.send_header('Last-Modified', self.date_time_string(time.time()))
        self.end_headers()
        self.wfile.write('Response body\n')
        return

    def do_POST(self):
        log.info('Received POST request')
        content_len = int(self.headers.getheader('content-length', 0))
        post_body = self.rfile.read(content_len)
        data = json.loads(post_body)
        log.info("Received {} data in Post request".format(data))
        server_received_data.append(data)
        log.info("Appended POST data payload to server_received_data")
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        return


class WebServer(object):
    def __init__(self, port=8080):
        self.port = port
        self.server = HTTPServer(('', port), HttpHandler)

    def start(self):
        thread = threading.Thread(target=self.server.serve_forever)
        thread.daemon = True
        try:
            thread.start()
        except Exception as e:
            raise ValueError("Caught exception could not launch webserver thread", e)

    def stop(self):
        self.server.shutdown()

    def get_data(self):
        return server_received_data
