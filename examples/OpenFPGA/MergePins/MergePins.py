import os
from spydrnet.ir.innerpin import InnerPin
from spydrnet.ir import cable
from spydrnet.ir.port import Port
from spydrnet.ir.instance import Instance
import spydrnet as sdn
import logging

from pprint import pprint
from itertools import combinations
from spydrnet.util import selection
from spydrnet.util.selection import Selection


logger = logging.getLogger(__name__)
FORMAT = "%(levelname)5s (%(lineno)4s) - %(message)s"



logging.basicConfig(level=logging.INFO, format=FORMAT)

def MergePins( definition, pins=None, testrun=False):

    duplicatePins = []
    defPort = list(definition.get_ports())
    for fromPort,toPort in combinations(defPort, 2):
        if fromPort is toPort:
            continue
        elif len(fromPort.pins) == len(toPort.pins):
            sameNet = True
            for eachPin1, eachPin2 in zip(fromPort.pins,toPort.pins):
                for eachInst in definition.references:
                    eachPin1 = eachInst.pins[eachPin1]
                    eachPin2 = eachInst.pins[eachPin2]
                    if not eachPin1.wire == eachPin2.wire:
                        sameNet = False
            if sameNet:
                logger.info(f"Can Merge {fromPort.name} {toPort.name}")
                duplicatePins.append((fromPort, toPort))

    if testrun:
        return duplicatePins

    for port1, port2 in duplicatePins:
        for eachP1Pin in port1.pins:
            ww = eachP1Pin.wire
            wwIndex = eachP1Pin.wire.index()

            # Remove all internal connection
            wwP2= port2.pins[wwIndex].wire
            for eachPin in wwP2.get_pins(selection=selection.OUTSIDE):
                eachPin.wire.disconnect_pin(eachPin)
                ww.connect_pin(eachPin)
            definition.remove_cable(wwP2.cable)
        definition.remove_port(port2)
    return duplicatePins

dir_path = os.path.dirname(os.path.realpath(__file__))
netlist = sdn.parse(os.path.join(dir_path, "hierDesign.v"))

work = next(netlist.get_libraries("work"))
topModule = next(work.get_definitions("top"))
module1 = next(work.get_definitions("module1"))
inst_m1_1 = next(topModule.get_instances("inst_m1_1"))
inst_m1_2 = next(topModule.get_instances("inst_m1_2"))

MergePins(module1)

sdn.compose(netlist, os.path.join(dir_path, "_result.v"))
for eachDef in work.get_definitions():
    eachDef.name += "_eq"
sdn.compose(netlist, os.path.join(dir_path, "_result_equiv.v"))
