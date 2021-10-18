import os
from spydrnet.ir import cable
from spydrnet.ir.port import Port
from spydrnet.ir.instance import Instance
from spydrnet.ir.definition import Definition
from spydrnet.ir.innerpin import InnerPin
from spydrnet.ir.outerpin import OuterPin
import spydrnet as sdn
import logging
from random import randint


logger = logging.getLogger(__name__)
FORMAT = "%(levelname)5s (%(lineno)4s) - %(message)s"



logging.basicConfig(level=logging.INFO, format=FORMAT)
# filename=f'{__name__}.log',
# filemode="w")

def RestructureInstance(topModule, modulelist, useDefinition, Pinmap, newInstanceName=None):
    # Create instance of the module
    newInstanceName = newInstanceName or f"{useDefinition.name}_{randint(1,10)}"
    MergedModule = topModule.create_child( name=newInstanceName,
                    reference=useDefinition)

    for index, eachM in enumerate(modulelist):
        for p in eachM.get_ports():
            DestPort = next(MergedModule.get_ports(Pinmap[eachM.reference.name][index][p.name]))
            for w in p.pins:
                origPin = eachM.pins[w]
                WireIndex = w.index()
                origPin.wire.connect_pin(MergedModule.pins[DestPort.pins[WireIndex]])

    for eachM in modulelist:
        topModule.remove_child(eachM)


def MergeModules(topModule, modulelist,  newModuleName=None, Pinmap=None):
    """
    topModule : Temporary argument to create new module definition,
                It will be replaced, when this fucntion moves to library class
    modulelist: List of modules to merge together
    Pinmap:     Optional argument to provide pin rename mapping in case of conflict
    useDefinition:     Optional argument, if provided instead of creating new module it will reuse this definition
    newModuleName:  Optional argument, to give specific name to new module
                    Default name: <moduel1>_<module2>...<module.>_merge
    """

    RenameMap = {} # Suppose to store pin rename map

    # Sanity checks
    for eachModule in modulelist:
        assert isinstance(eachModule, Instance), "Modulelist contains none non-intance object"

    # Create a new module
    if not newModuleName:
        newModuleName = "_".join([each.reference.name for each in modulelist]) + "_merged"
        print(f"Inferred module name {newModuleName} ")
    newMod = topModule.library.create_definition(name=newModuleName)

    # Create instance of the module
    MergedModule = topModule.create_child( name=f"{newModuleName}_1",
                    reference=newMod)

    for index, eachM in enumerate(modulelist):
        logger.info(f"******************************************************")
        logger.info(f"Iterating module {eachM.name} [{eachM.reference.name}]")
        logger.info(f"******************************************************")


        # AddPorts
        RenameMap[eachM.reference.name]= {}
        currMap = {}
        RenameMap[eachM.reference.name][index] = currMap
        for p in eachM.get_ports():
            pClone = p.clone()
            for eachSuffix in [""]+[f"_{i}" for i in range(10)]:
                newName = pClone.name + eachSuffix
                if not len(list(newMod.get_ports(newName))):
                    break

            for eachPin in p.pins:
                ClonedPin = eachPin.clone()
                ClonedPin._wire = eachPin._wire.clone()
                if eachPin.index() == 0:
                    newCable = eachPin._wire.cable.clone()

                ClonedPin._wire._cable = newCable
                pClone.add_pin(ClonedPin,eachPin.index())
                pClone.remove_pin(pClone._pins[-1])

            pClone.change_name(newName)

            currMap[p.name] = newName
            newMod.add_port(pClone)

            for eachPin in p.pins:
                instOutPin = eachM.pins[eachPin]
                conWire = instOutPin.wire
                instPin = MergedModule.pins[pClone.pins[eachPin.index()]]
                conWire.connect_pin(instPin)
                instOutPin.wire.disconnect_pin(instOutPin)
                newCable.wires[eachPin.index()].connect_pin(instOutPin)

        topModule.remove_child(eachM)
        newMod.add_child(eachM)
    return newMod, RenameMap



dir_path = os.path.dirname(os.path.realpath(__file__))
netlist = sdn.parse(os.path.join(dir_path, "hierDesign.v"))

work = next(netlist.get_libraries("work"))
topModule = next(work.get_definitions("top"))
MOD1 = next(work.get_definitions("mod1"))
MOD2 = next(work.get_definitions("mod2"))


MOD1_1 = next(topModule.get_instances("mod1_1"))
MOD2_1 = next(topModule.get_instances("mod2_1"))
MOD1_2 = next(topModule.get_instances("mod1_2"))
MOD2_2 = next(topModule.get_instances("mod2_2"))


topModule.merge_instance([MOD1_2, MOD2_2])
# newMod, RenameMap = MergeModules(topModule, [MOD1_1, MOD2_1])
# RestructureInstance(topModule, [MOD1_2, MOD2_2],
#                     newInstanceName=f"{newMod.name}_2",
#                     useDefinition=newMod,
#                     Pinmap=RenameMap)


sdn.compose(netlist, os.path.join(dir_path, "_result.v"))
MOD3 = next(topModule.get_instances("MOD3_1"))
# print([n.name for n in MOD3._cables])
netlist.top_instance = MOD3

print(MOD3.reference.cables)
print(MOD3.reference._children)
print(MOD3.is_leaf())


for eachDef in work.get_definitions():
    eachDef.name += "_eq"

sdn.compose(netlist, os.path.join(dir_path, "_result_equiv.v"))
# print([n.name for n in MOD1._cables])
# Finished the merging part
# Work on internal wires
# Merging ports
# And writing tests