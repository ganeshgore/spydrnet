from collections import deque, OrderedDict
from spydrnet.ir import instance
from spydrnet.ir.outerpin import OuterPin
from spydrnet.util import selection
from spydrnet.ir.port import Port
from spydrnet.ir.cable import Cable
import json
from itertools import chain
from spydrnet.ir.innerpin import InnerPin
from pprint import pformat, pprint
from copy import deepcopy
from collections import OrderedDict
import spydrnet.parsers.verilog.verilog_tokens as vt
from spydrnet.composers.html.SpyDrNetEncoder import SpyDrNetJSONEncoder


InputFilter  = lambda x: x.direction == Port.Direction.IN
OutputFilter = lambda x: (x.direction == Port.Direction.OUT) or (x.direction == Port.Direction.INOUT)


class HTMLComposer:

    def __init__(self, definition_list=None, write_blackbox=False):
        self.file = None
        self.direction_string_map = dict()
        self.direction_string_map[Port.Direction.IN] = "INPUT"
        self.direction_string_map[Port.Direction.OUT] = "OUTPUT"
        self.direction_string_map[Port.Direction.INOUT] = "INPUT"
        self.direction_side_map = dict()
        self.direction_side_map[Port.Direction.IN] = "WEST"
        self.direction_side_map[Port.Direction.OUT] = "EAST"
        self.direction_side_map[Port.Direction.INOUT] = "WEST"
        # self.direction_string_map[Port.Direction.UNDEFINED] = "/* undefined port
        self.depth = 2
        self.write_blackbox = write_blackbox
        self.definition_list = definition_list
        self.ElkJSON = ''
        self.edgeID = 1
        self.ModuleList = {}

    def run(self, ir, file_out="out.v"):
        """ Main method to run composer """
        self.file = file_out
        self._compose(ir)


    def _get_default_module_template(self, hinstance):
        instance = hinstance.item
        od = OrderedDict()
        od["id"]= hinstance.name
        od["ports"]= []
        od["hwMeta"]= { "bodyText": instance.name, "cls": "Process", }
        od["_edges"]= []
        od["_children"]= []
        od["properties"]= {
                "org.eclipse.elk.layered.mergeEdges": 1,
                "org.eclipse.elk.portConstraints": "FIXED_SIDE"
            }
        return od

    def _get_default_port_template(self, portInstance):
        return  {
            "id": portInstance.name,
            "direction": self.direction_string_map[portInstance.direction],
            "hwMeta": { "name": portInstance.name },
            "properties": {
                "index": 1,
                "side": self.direction_side_map[portInstance.direction]
            }
        }

    def _get_default_net_template(self, cableInstance, segement=0):
        return  {
          "id": cableInstance.name,
          "hwMeta": {
              "name": f"{cableInstance.name}" if not segement else f"{cableInstance.name}[{segement}]",
               "cssClass": "link-style0",
              },
          "source": "",
          "sourcePort": "",
          "target": "",
          "targetPort": ""
        }

    def _create_component_body(self, hinstance, node):
        """ This creates the component body with input and Output ports
        children and edges kept empty to fill up later
        """
        instance = hinstance.item

        for eachPort in chain(instance.get_ports(filter=InputFilter), instance.get_ports(filter=OutputFilter)):
            portNode = self._get_default_port_template(eachPort)
            portNode["id"] = hinstance.name + "/" +portNode["id"]
            node["ports"].append(portNode)

    def _create_top_frame(self):
        return {
            "id": "top_frame",
            "children": [],
            "edges": [],
            "ports": [],
            "hwMeta": {},
            "properties": {
                "org.eclipse.elk.layered.mergeEdges": 1,
                "org.eclipse.elk.portConstraints": "FIXED_SIDE"
                }
        }

    def _create_top_block(self, name="unnamed block"):
        return {
            "id": "top",
            "_children": [],
            "_edges": [],
            "ports": [],
            "hwMeta": { "bodyText": name, "cls": "Process",},
            "properties": {
                "org.eclipse.elk.layered.mergeEdges": 1,
                "org.eclipse.elk.portConstraints": "FIXED_SIDE"
                }
        }

    def _add_edges(self, netlist, curr_pointer):
        for eachhCable in netlist.get_hcables():
            eachCable = eachhCable.item
            edge = self._get_default_net_template(eachCable)
            hWires = list(eachhCable.get_hwires())
            TotalWires = len(hWires)
            if TotalWires == 1:
                edge["id"] = self.edgeID
                self.edgeID += 1
                for indx, eachPin in enumerate(hWires[0].get_hpins()):
                    if indx == 0:
                        edge["sources"].append([
                            "/".join(eachPin.name.split("/")[:-1]) or "top",
                            eachPin.name])
                    else:
                        edge["targets"].append([
                            "/".join(eachPin.name.split("/")[:-1]) or "top",
                            eachPin.name])
                curr_pointer["_edges"].append(edge)


    def _create_top_component_tree(self, netlist, curr_pointer, depth):
        if depth > self.depth:
            return
        for eachTopLevelInstance in netlist.get_hinstances():
            print(eachTopLevelInstance.name)
            node = self._get_default_module_template(eachTopLevelInstance)
            self._create_component_body(eachTopLevelInstance, node)
            curr_pointer["_children"].append(node)
            # for child in eachTopLevelInstance.get_hinstances():
            self._create_top_component_tree(eachTopLevelInstance, node, depth+1)
        self._add_edges(netlist, curr_pointer)


    def _compose(self, netlist):
        """ Identifies the top level instance """
        instance = netlist.top_instance
        assert instance != None, " Missing top instance "
        self.ElkJSON = self._create_top_frame()
        TopNode = self._create_top_block(instance.reference.name)
        self.ElkJSON["children"].append(TopNode)

        for eachPort in chain(instance.get_ports(filter=InputFilter), instance.get_ports(filter=OutputFilter)):
            portNode = self._get_default_port_template(eachPort)
            portNode["id"] = portNode["id"]
            TopNode["ports"].append(portNode)


        self._create_top_component_tree(netlist, TopNode, 1)
        self.ElkJSON["hwMeta"]["maxId"] = self.edgeID
        self._write_html()

    def _write_html(self):
        fp = open(self.file, "w")
        fp.write("""
        <!DOCTYPE html><html><head>
        <meta charset="utf-8">
        <title>SpyDrNet Schematic Render</title>
        <script type="text/javascript" src="https://cdnjs.cloudflare.com/ajax/libs/d3/7.0.2/d3.js"></script>
        <script type="text/javascript" src="https://cdn.jsdelivr.net/npm/elkjs@0.7.0/lib/elk.bundled.js"></script>
        <script type="text/javascript" src="https://cdn.jsdelivr.net/npm/d3-hwschematic@0.1.6/dist/d3-hwschematic.js"></script>
        <link href="https://cdn.jsdelivr.net/npm/d3-hwschematic@0.1.6/dist/d3-hwschematic.css" rel="stylesheet">
        <style> body { margin: 0; background-color: white; } </style> </head>
        <body>
            <svg id="scheme-placeholder"></svg>
            <script>
                function viewport() {
                    var e = window, a = 'inner';
                    if (!('innerWidth' in window)) {
                        a = 'client';
                        e = document.documentElement || document.body;
                    }
                    return { width: e[a + 'Width'], height: e[a + 'Height']}
                }

                var width = viewport().width,
                    height = viewport().height;

                var svg = d3.select("#scheme-placeholder")
                    .attr("width", width)
                    .attr("height", height);

                var orig = document.body.onresize;
                document.body.onresize = function(ev) {
                    if (orig)
                        orig(ev);

                    var w = viewport();
                    svg.attr("width", w.width);
                    svg.attr("height", w.height);
                }

                var hwSchematic = new d3.HwSchematic(svg);
                var zoom = d3.zoom();
                zoom.on("zoom", function applyTransform(ev) {
                    hwSchematic.root.attr("transform", ev.transform)
                });

                // disable zoom on doubleclick
                // because it interferes with component expanding/collapsing
                svg.call(zoom)
                .on("dblclick.zoom", null)
        \n""")
        fp.write("hwSchematic.bindData(\n")
        fp.write(json.dumps(self.ElkJSON, cls=SpyDrNetJSONEncoder,
            sort_keys=False, indent=2))
        fp.write(")")
        fp.write("""
        </script>
        </body>
        </html>
        """)
        fp.close()
