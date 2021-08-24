import os
import spydrnet as sdn
from pprint import pprint
from spydrnet.ir.instance import  Instance
from spydrnet.util.selection import Selection


"""
This example try to swap the nets connected to the instance on bus pins
"""

dir_path = os.path.dirname(os.path.realpath(__file__))
netlist = sdn.parse(os.path.join(dir_path, "busNetlist.v"))

work = next(netlist.get_libraries("work"))
topModule = next(work.get_definitions("top"))
or2 = next(topModule.get_instances("or2_1"))


# Get outerpin of the instance
AInputs = next(or2.get_cables("A"))
QOutput = next(or2.get_cables("Q"))
# Get wire connected to the outer pin
AOuterPin = list(AInputs.get_pins(selection=Selection.OUTSIDE))
QOuterPin = next(QOutput.get_pins(selection=Selection.OUTSIDE))

# Disconnect wire connected to the port
QOuterPin.wire.disconnect_pin(QOuterPin)
[w.wire.disconnect_pin(w) for w in AOuterPin]

sdn.compose(netlist, os.path.join(dir_path, "_result.v"))
