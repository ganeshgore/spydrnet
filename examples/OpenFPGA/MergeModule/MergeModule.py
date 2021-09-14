import os
from spydrnet.ir.port import Port
from spydrnet.ir.instance import Instance
from spydrnet.ir.definition import Definition
from spydrnet.ir.innerpin import InnerPin
from spydrnet.ir.outerpin import OuterPin
import spydrnet as sdn
from spydrnet.util import selection
from spydrnet.util.selection import Selection
from pprint import pprint
import logging

logger = logging.getLogger(__name__)
FORMAT = "%(levelname)5s (%(lineno)4s) - %(message)s"



logging.basicConfig(level=logging.INFO, format=FORMAT)

def MergeModules(topModule, modulelist, useDefinition=None, newModuleName=None):
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
    IncomingWires = []

    # Sanity checks
    for eachModule in modulelist:
        assert isinstance(eachModule, Instance), "Modulelist contains none non-intance object"

    # Create a new module
    if not useDefinition:
        if not newModuleName:
            newModuleName = "_".join([each.reference.name for each in modulelist]) + "_merged"
            print(f"Inferred module name {newModuleName} ")
        newMod = topModule.library.create_definition(name=newModuleName)
    else:
        assert isinstance(useDefinition, Definition), "useDefinition should be definition object"
        newMod= useDefinition

    # Create instance of the module
    MergedModule = topModule.create_child( name=f"{newModuleName}_1",
                    reference=newMod)

    for eachM in modulelist:
        logger.info(f"******************************************************")
        logger.info(f"Iterating module {eachM.name} [{eachM.reference.name}]")
        logger.info(f"******************************************************")


        # AddPorts
        RenameMap[eachM.name] = {}
        for p in eachM.get_ports():
            pClone = p.clone()
            for eachSuffix in [""]+[f"_{i}" for i in range(10)]:
                newName = pClone.name + eachSuffix
                if not len(list(newMod.get_ports(newName))):
                    break
            pClone.name = newName

            for eachPin in p.pins:
                ClonedPin = eachPin.clone()
                ClonedPin._wire = eachPin._wire.clone()
                if eachPin.index() == 0:
                    newCable = eachPin._wire.cable.clone()
                    newCable.name = newName

                ClonedPin._wire._cable = newCable
                pClone.add_pin(ClonedPin,eachPin.index())
                pClone.remove_pin(pClone._pins[-1])

            RenameMap[eachM.name][p.name] = newName
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
    return RenameMap


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
logger.info("Finishing script")