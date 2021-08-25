import os
from spydrnet.ir.innerpin import InnerPin
from spydrnet.ir.outerpin import OuterPin
import spydrnet as sdn
from spydrnet.util import selection
from spydrnet.util.selection import Selection
from pprint import pprint

def CreateFTPinsForCables(cable, module):
    PortName = cable.name
    return (
            module.create_port(f"{PortName}_ft_in",
                    is_scalar=cable.is_scalar,
                    lower_index=cable.lower_index,
                    direction=sdn.IN).create_pins(len(cable.wires)),
            module.create_port(f"{PortName}_ft_out",
                    is_scalar=cable.is_scalar,
                    lower_index=cable.lower_index,
                    direction=sdn.OUT).create_pins(len(cable.wires))
        )


def CreateFeedthrough(topModule, cable, instance, suffixPort="ft", suffixnet="ft"):
    print(f"======================================")
    print(f"Cable Name {cable.name}")
    print(f"Instance Name {instance.name}")
    print(f"Instance reference Name {instance.reference.name}")
    inPort, OutPort = CreateFTPinsForCables(cable,instance.reference)
    c = cable.clone()
    c.name += "_ft"
    topModule.add_cable(c)

    for indx, eachW in enumerate(cable.wires):
        DriverPins = list(filter(lambda a: isinstance(a, InnerPin), eachW.pins))
        LoadPins = list(filter(lambda a: isinstance(a, OuterPin), eachW.pins))

        w = c.wires[eachW.index()]
        eachW.disconnect_pins_from(LoadPins)
        for eachLoadPin in LoadPins:
            print(f"eachLoadPin {eachLoadPin}")
            w.connect_pin(eachLoadPin)

        eachW.connect_pin(instance.pins[inPort[indx]])
        w.connect_pin(instance.pins[OutPort[indx]])
    print(f"======================================")
    return c

dir_path = os.path.dirname(os.path.realpath(__file__))
netlist = sdn.parse(os.path.join(dir_path, "hierDesign.v"))

work = next(netlist.get_libraries("work"))
topModule = next(work.get_definitions("top"))
MOD1 = next(work.get_definitions("MOD1"))
MOD2 = next(work.get_definitions("MOD2"))
MOD1_1 = next(topModule.get_instances("mod1_1"))
MOD2_1 = next(topModule.get_instances("mod2_1"))

pp1 = MOD2_1.pins[next(MOD2_1.get_ports("bus1")).pins[0]]
pp2 = MOD2_1.pins[next(MOD2_1.get_ports("bus1")).pins[1]]


CreateFeedthrough(topModule,
                next(topModule.get_cables("n2")),
                next(topModule.get_instances("mod1_1")))

CreateFeedthrough(topModule,
                next(topModule.get_cables("bus1")),
                next(topModule.get_instances("mod1_1")))

sdn.compose(netlist, os.path.join(dir_path, "_result.v"))
