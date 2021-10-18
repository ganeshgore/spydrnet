
import logging
import os
import io
from svgwrite import Drawing
from svgwrite.container import Group
from spydrnet.util.ui_servers import httpThread
from spydrnet.util.ui_servers import wsServerThread
from spydrnet.util.ui_servers import webHandler
from spydrnet.util.get_floorplan import FloorPlanViz

logger = logging.getLogger('spydrnet_logs')
base_dir = os.path.dirname(os.path.abspath(__file__))

WS_PORT = 9000

PROPERTY = "VERILOG.InlineConstraints"

PIN_H = 4
PIN_W = 4


class start_gui(object):

    def __init__(self, address="127.0.0.1", httport=7000, wsPort=7001):
        global WS_PORT
        WS_PORT = wsPort
        self.http = httpThread(('0.0.0.0', 7000), webHandler)
        self.ws = wsServerThread()
        logger.info(f"Starting server on http://{address}:{httport}")

    def show_schematic(self):
        """ Uses schematic_render.html template to render hwELK JSON
        """
        pass

    def add_port(self, svgRoot):
        pass

    def show_floorplan(self, module):
        fp = FloorPlanViz(module)
        fp.compose()
        dwg = fp.get_svg()
        dwg.saveas("_sample.svg", pretty=True, indent=4)
        command = {
            "command" : "update_svg",
            "content" : dwg.tostring()
        }
        self.ws.send_to_all(command)

    def refresh_page(self):
        self.ws.send_to_all({"command" : "refresh_page"})

    def close(self):
        self.ws.ws.close_server()
        self.http.shutdown()
