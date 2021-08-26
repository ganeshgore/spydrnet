import os
from spydrnet.ir.port import Port
from spydrnet.ir.innerpin import InnerPin
from spydrnet.ir.outerpin import OuterPin
import spydrnet as sdn
from spydrnet.util import selection
from spydrnet.util.selection import Selection
from pprint import pprint

def MergeModules(topModule, modulelist, newModuleName="mergedModule"):
    RenameMap = {}
    newMod = topModule.library.create_definition(name=newModuleName)
    MergedModule = topModule.create_child( name=f"{newModuleName}_1",
                    reference=newMod)
    for eachM in modulelist:
        RenameMap[eachM.name] = {}
        for p in eachM.get_ports():
            pClone = p.clone()
            for eachSuffix in [""]+[f"_{i}" for i in range(10)]:
                newName = pClone.name + eachSuffix
                if not len(list(newMod.get_ports(newName))):
                    break
            pClone.name = newName
            RenameMap[eachM.name][p.name] = newName
            newMod.add_port(pClone)
            ww = newMod.create_cable(newName).create_wires(len(p.pins))
            print(f"Adding port {pClone.name}")

            for pin in p.get_pins(selection=selection.OUTSIDE):
                print(pin.wire.index())
                print(MergedModule.pins[pClone.pins[pin.wire.index()]])
                pin.wire.connect_pin(MergedModule.pins[pClone.pins[pin.wire.index()]])
                currWW = ww[pin.wire.index()]
                inPin = eachM.pins[pin.inner_pin]
                inPin.wire.disconnect_pin(inPin)
                currWW.connect_pin(inPin)

        topModule.remove_child(eachM)
        newMod.add_child(eachM)

    pprint(RenameMap)


dir_path = os.path.dirname(os.path.realpath(__file__))
netlist = sdn.parse(os.path.join(dir_path, "hierDesign.v"))

work = next(netlist.get_libraries("work"))
topModule = next(work.get_definitions("top"))
MOD1 = next(work.get_definitions("MOD1"))
MOD2 = next(work.get_definitions("MOD2"))
MOD1_1 = next(topModule.get_instances("mod1_1"))
MOD2_1 = next(topModule.get_instances("mod2_1"))


MergeModules(topModule, [MOD1_1, MOD2_1])

sdn.compose(netlist, os.path.join(dir_path, "_result.v"))

for eachDef in work.get_definitions():
    eachDef.name += "_eq"
sdn.compose(netlist, os.path.join(dir_path, "_result_equiv.v"))
