import os
import spydrnet as sdn
from pprint import pprint
from spydrnet.ir.instance import  Instance
from spydrnet.util.selection import Selection


dir_path = os.path.dirname(os.path.realpath(__file__))
netlist = sdn.parse(os.path.join(dir_path, "busNetlist.v"))

work = next(netlist.get_libraries("work"))
topModule = next(work.get_definitions("top"))
or2 = next(topModule.get_instances("or2_1"))

APort = next(or2.get_ports("A"))
print(f"Current port name {APort.name}")

# next(APort.get_cables(APort.name)).name = "Ain"
APort.change_name("Ain")

print(f"Renamed port name {APort.name}")

sdn.compose(netlist, os.path.join(dir_path, "_result.v"))
