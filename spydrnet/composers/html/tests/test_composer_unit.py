import unittest
from unittest.case import expectedFailure
import spydrnet as sdn
import json
from spydrnet.composers.html.composer import HTMLComposer


class TestHTMLComposer(unittest.TestCase):

    def setUp(self) -> None:
        self.composer = HTMLComposer()
        self.netlist = sdn.Netlist()

    def match_output(self, expectedOutput, Output):
        if isinstance(expectedOutput, str):
            expectedOutput = json.dumps(expectedOutput, separators=(',', ':'))
        if isinstance(Output, str):
            Output = json.dumps(Output, separators=(',', ':'))
        assert expectedOutput == Output
        return True

    def test_write_json(self):
        ELKString = """{\n  "id": "1",\n  "hwMeta": { "name": "wire", "bodyText": "something"},\n  "children": []}""".strip()
        self.composer.ElkJSON = json.loads(ELKString)
        writtenStr = self.composer._write_json()
        assert ELKString == str(writtenStr), "JSON format is not compacted"

    def test_get_default_module_template(self):
        ELKJsonObj = {
            "id": "top/instance",
            "ports": [],
            "hwMeta": {"bodyText": "instanceName", "cls": "Process", },
            "_edges": [],
            "_children": [],
            "properties": {
                "org.eclipse.elk.layered.mergeEdges": 1,
                "org.eclipse.elk.portConstraints": "FIXED_SIDE"
            }
        }
        output = self.composer._get_default_module_template(
            "top/instance", "instanceName")
        self.assertTrue(self.match_output(ELKJsonObj, output),
                    "Wrong default value for module")

    def test_get_default_port_template(self):
        PortName = "ModulePort"
        port = sdn.Port(name=PortName, direction=sdn.Port.Direction.IN)
        ELKJsonObj = {
            "id": PortName,
            "direction": "INPUT",
            "hwMeta": { "name": PortName },
            "properties": {
                "index": 1,
                "side": "WEST"
            }
        }
        output = self.composer._get_default_port_template(port)
        self.assertTrue(self.match_output(ELKJsonObj, output),
                    "Wrong default value for port")
