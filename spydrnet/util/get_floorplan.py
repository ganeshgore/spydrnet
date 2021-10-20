import os
import logging
from spydrnet.ir.outerpin import OuterPin
from typing import NewType
from svgwrite import Drawing
from svgwrite.shapes import Polyline
from svgwrite.container import Group


logger = logging.getLogger('spydrnet_logs')
base_dir = os.path.dirname(os.path.abspath(__file__))
PROJ_BASE_DIR = os.path.abspath(os.path.join(base_dir, ".."))

PROPERTY = "VERILOG.InlineConstraints"

PIN_H = 4
PIN_W = 4


class FloorPlanViz:

    def __init__(self, definition, viewbox=(0, 0, 1000, 1000)):
        self.module = definition
        # self.dwg = Drawing(style="background:red")
        self.dwg = Drawing()
        self.dwg.viewbox(*viewbox)
        self.defList = {}

        # Create groups
        self.dwgbg = self.dwg.add(Group(id="bg"))
        self.dwgMain = self.dwg.add(Group(id="mainframe"))
        self.dwgShapes = self.dwgMain.add(Group(id="mainShapes",transform="scale(1,-1)"))
        self.dwgText = self.dwgMain.add(Group(id="mainText",transform="scale(1,-1)"))
        self.dwgEdges = self.dwgMain.add(Group(id="edges",transform="scale(1,-1)"))

        # SVG size
        self.view_w = 0
        self.view_h = 0
        self.add_stylehseet()

    def add_stylehseet(self):
        self.dwg.defs.add(self.dwg.style("""
            text{font-family: LATO; font-weight: 800; font-size: 5px;}
            .module_boundary{fill:#f4f0e6}
            .left_pin{
                fill:blue;
                text-anchor: start;
                transform: translate(5px, 00px) scale(1,-1);}
            .right_pin{
                fill:blue;
                text-anchor: end;
                transform: translate(-5px, 00px) scale(1,-1);}
            .bottom_pin{
                fill:blue;
                transform-box: fill-box;
                transform-origin: start;
                text-anchor: start;
                transform: translate(0px, 10px) rotate(90deg) scale(1,-1);}
            .top_pin{
                fill:blue;
                transform-box: fill-box;
                transform-origin: bottom left;
                text-anchor: start;
                transform: translate(0px, -3px) rotate(-90deg) scale(1,-1);}
            .in_pin{fill: red;}
            .out_pin{fill: blue;}
        """))

    def update_viewbox(self, x, y):
        self.view_w = self.view_w if self.view_w > x else x
        self.view_h = self.view_h if self.view_h > y else y

    def add_symbol(self, module):
        if self.defList.get(module.name, None):
            return self.defList[module.name]
        width = int(module.data[PROPERTY].get("WIDTH", 10))
        height = int(module.data[PROPERTY].get("HEIGHT", 10))
        new_def = self.dwg.symbol(id=module.name)
        self.defList[module.name] = {
            "name": module.name,
            "instance": new_def,
            "width": width,
            "height": height,
        }
        new_def.add(self.dwg.rect(insert=(1, 1),
                                  size=(width-1, height-1),
                                  class_="module_boundary",
                                  stroke="grey",
                                  fill="white",
                                  stroke_width=2))

        for port in module.ports:
            p = port.name
            SIDE = module.data[PROPERTY].get(f"{p}_SIDE", [])
            OFFSET = int(module.data[PROPERTY].get(f"{p}_OFFSET", 0))

            if 'left' in SIDE:
                LOC_X, LOC_Y = 2, height-OFFSET
                pin_w, pin_h = PIN_W, PIN_H
                mult = -1
            elif 'right' in SIDE:
                LOC_X, LOC_Y = width-1, height-OFFSET
                pin_w, pin_h = PIN_W, PIN_H
                mult = -1
            elif 'bottom' in SIDE:
                LOC_X, LOC_Y = width-OFFSET+1, 2
                pin_w, pin_h = PIN_H, PIN_W
                mult = 1
            elif 'top' in SIDE:
                LOC_X, LOC_Y = width-OFFSET+1, height-1-PIN_W
                pin_w, pin_h = PIN_H, PIN_W
                mult = 1
            else:
                LOC_X, LOC_Y = width/2, height/2
                pin_w, pin_h = PIN_W, PIN_H
                mult = -1

            new_def.add(self.dwg.rect(insert=(LOC_X-pin_w*0.5, LOC_Y-pin_h*0.5),
                                      size=(pin_w, pin_h),
                                      class_=f"module_pin {str(port.direction).split('.')[-1].lower()}_pin",
                                      onmousemove=f"showTooltip(evt, '{port.name}');",
                                      onmouseout="hideTooltip();",
                                      stroke_width=0))
            new_def.add(self.dwg.text(port.name,
                                    insert=(LOC_X-pin_w*0.5, mult*(LOC_Y-pin_h*0.5)),
                                    class_=f"pin {SIDE}_pin",))

            # transform=f"translate({OFF_X}, {OFF_Y}) rotate({ROT}) " + "scale(1,-1)",
            module.data[PROPERTY][f"{p}_X"] = LOC_X
            module.data[PROPERTY][f"{p}_Y"] = LOC_Y

        self.dwg.defs.add(new_def)
        return new_def

    def add_background(self, bgColor="#FFF"):
        self.dwgbg.add(self.dwg.rect(insert=(-25, -25),
                                     size=(self.view_w+50,
                                           self.view_h+50),
                                     id=f"background",
                                     fill=bgColor,
                                     stroke_width=0))
        self.dwg.viewbox(-50, -1*(self.view_h+100), self.view_w+100, self.view_h+100)

    def add_top_block(self, top_module):
        name = top_module.name
        defDict = self.defList[name]
        self.dwgShapes.add(self.dwg.use(defDict["instance"],
                                        class_=f"topModule",
                                        insert=(0, 0)))
        self.dwgText.add(self.dwg.text(defDict["name"],
                                       insert=(defDict["width"]*0.5,
                                               -1*defDict["height"]*0.1),
                                       fill="black",
                                       transform="scale(1,-1)",
                                       alignment_baseline="middle",
                                       text_anchor="middle"))
        self.update_viewbox(defDict["width"], defDict["height"])

    def get_label_location(self, instance):
        defDict = self.defList[instance.reference.name]
        loc_x = int(instance.data[PROPERTY].get("LOC_X", 0))
        loc_y = int(instance.data[PROPERTY].get("LOC_Y", 0))
        loc_x += defDict["width"]*0.5
        loc_y += 20
        loc_y *= -1
        # loc_y += defDict["height"]*0.5
        return (loc_x, loc_y)

    def add_block(self, instance):
        name = instance.reference.name
        defDict = self.defList[name]

        loc_x = int(instance.data[PROPERTY].get("LOC_X", 0))
        loc_y = int(instance.data[PROPERTY].get("LOC_Y", 0))

        self.dwgShapes.add(self.dwg.use(defDict["instance"],
                                        class_=f"{instance.name}",
                                        insert=(loc_x, loc_y)))
        self.dwgText.add(self.dwg.text(f"{instance.name}",
                                       insert=self.get_label_location(
                                           instance),
                                       transform="scale(1,-1)",
                                       fill="black",
                                       alignment_baseline="middle",
                                       text_anchor="middle"))

    def compose(self):
        self.add_symbol(self.module)
        self.add_top_block(self.module)
        for child in self.module.children:
            self.add_symbol(child.reference)
            self.add_block(child)

        for cable in self.module.get_cables():
            if cable.size:
                points = []
                for p in cable.wires[0].pins:
                    x, y = 0, 0
                    if isinstance(p, OuterPin):
                        x = int(p.instance.data[PROPERTY].get("LOC_X", 0))
                        y = int(p.instance.data[PROPERTY].get("LOC_Y", 0))
                        m = p.instance.reference
                        x += int(m.data[PROPERTY].get(f"{p.port.name}_X", 0))
                        y += int(m.data[PROPERTY].get(f"{p.port.name}_Y", 0))
                    else:
                        x = int(self.module.data[PROPERTY].get(
                            f"{p.port.name}_X", 0))
                        y = int(self.module.data[PROPERTY].get(
                            f"{p.port.name}_Y", 0))
                    points.append((x, y))
                if(points):
                    self.dwgEdges.add(
                        Polyline(points, fill="none",
                                 class_="edge",
                                 stroke="black",
                                 onmousemove=f"showTooltip(evt, '{cable.name}');",
                                 onmouseout="hideTooltip();",
                                 stroke_width="1"))

    def get_svg(self):
        self.add_background()
        return self.dwg

    def get_html(self):
        self.get_svg()
        static_root = os.path.join(PROJ_BASE_DIR, "support_files")
        with open(os.path.join(static_root, "html_templates",
                               "svg_render.html"), "rb") as fp:
            content = fp.read()

        script = """function load_svg() {
            d3.select("#svgViewer").html(`%s`)}""" % self.dwg.tostring()

        content = content.replace(
            'onload="init_websocket();"'.encode(),
            'onload="load_svg();"'.encode(),
        )
        content = content.replace(
            '// <ADDITIONAL JS>'.encode(),
            script.encode(),
        )
        return content
