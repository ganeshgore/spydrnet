import os
import json
import threading
import socketserver
import time
from websock import WebSocketServer
from http.server import HTTPServer, BaseHTTPRequestHandler
import logging

logger = logging.getLogger('spydrnet_logs')
base_dir = os.path.dirname(os.path.abspath(__file__))

WS_PORT = 9000
TEMPLATE = "SVG"


class webHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        static_root = os.path.join(base_dir, "..", "support_files")
        self.send_response(200)
        if self.path == '/':
            self.end_headers()
            if TEMPLATE in ["SVG", "FLOORPLAN"]:
                content = self.get_svg_template()
            else:
                with open(os.path.join(static_root, "html_templates",
                                       "interface.html"), "rb") as fp:
                    content = fp.read()
                content = content.replace(
                    "<SOCKET_URL>".encode(),
                    f"ws://localhost:{WS_PORT}/".encode())
            self.wfile.write(content)
        else:
            filename = static_root + "/static_files" + self.path
            if filename[-4:] == '.css':
                self.send_header('Content-type', 'text/css')
            elif filename[-3:] == '.js':
                self.send_header('Content-type', 'application/javascript')
            else:
                self.send_header('Content-type', 'text/html')
            self.end_headers()
            with open(filename, 'rb') as fh:
                html = fh.read()
                self.wfile.write(html)

    def get_svg_template(self):
        static_root = os.path.join(base_dir, "..", "support_files")
        with open(os.path.join(static_root, "html_templates",
                               "svg_render.html"), "rb") as fp:
            content = fp.read()
        content = content.replace(
            "<SOCKET_URL>".encode(),
            f"ws://localhost:{WS_PORT}/".encode())
        return content


class httpThread(socketserver.ThreadingMixIn, socketserver.TCPServer):

    def __init__(self, *args):
        super(httpThread, self).__init__(*args)

        self.thread = threading.Thread(target=self.run, args=(), daemon=True)
        self.thread.daemon = True
        self.thread.start()

    def run(self):
        self.serve_forever()

    def set_template(self, template):
        global INDEX_PAGE
        INDEX_PAGE = template.upper()
        logger.warn(f"{template} Template not found ")

    def get_template(self):
        return INDEX_PAGE


class wsServerThread(object):
    def __init__(self, wsPort=9000):
        global WS_PORT
        self.ws = WebSocketServer("0.0.0.0", wsPort,
                                  on_data_receive=self.on_data_receive,
                                  on_connection_open=self.on_connection_open,
                                  on_error=self.on_error,
                                  on_connection_close=self.on_connection_close)

        self.thread = threading.Thread(target=self.run, args=(), daemon=True)
        self.thread.daemon = True
        self.thread.start()
        self.clients = []
        WS_PORT = wsPort

    def run(self):
        self.ws.serve_forever()

    def on_data_receive(self, client, data):
        """Called by the WebSocketServer when data is received."""

        if data == "disconnect":
            self.ws.close_client(client)
        else:
            data += '!'
            self.ws.send(client, data)

    def send_to_all(self, data):
        if not isinstance(data, str):
            data = json.dumps(data)
        for client in self.clients:
            self.ws.send(client, data)

    def send(self, client, data):
        if not isinstance(data, str):
            data = json.dumps(data)
        self.ws.send(client, data)

    def on_connection_open(self, client):
        """Called by the WebSocketServer when a new connection is opened.
        """
        self.send(client, {"command": "message",
                           "message": "Welcome to PhyFloTA"})
        self.clients.append(client)

    def on_error(self, exception):
        """Called when the server returns an error
        """
        raise exception

    def on_connection_close(self, client):
        """Called by the WebSocketServer when a connection is closed."""
        self.send(client,  {"command": "message",
                            "message": "Closing socket"})
        self.clients.remove(client)

    def on_server_destruct(self, ):
        """Called immediately prior to the WebSocketServer shutting down."""
        print("Websocket closing")
