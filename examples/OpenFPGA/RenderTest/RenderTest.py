import os
from spydrnet.ir import pin
from spydrnet.parsers.edif.edif_tokens import DIRECTION
import sys
from spydrnet.ir.instance import Instance
import spydrnet as sdn
import logging
import difflib
from pprint import pprint


import glob


logger = logging.getLogger(__name__)
FORMAT = "%(levelname)5s (%(lineno)4s) - %(message)s"



logging.basicConfig(level=logging.INFO, format=FORMAT)

dir_path = os.path.dirname(os.path.realpath(__file__))


for eachFile in glob.glob('./source/[a-zA-Z]*.v'):
    filename = os.path.splitext(os.path.basename(eachFile))[0]

    logger.info("==========================================================")
    logger.info(f"Reading design {eachFile}")
    netlist = sdn.parse(os.path.join(dir_path, eachFile))

    work = next(netlist.get_libraries("work"))
    topModule = next(work.get_definitions("top"))



    if filename == "hierDesign":
        module1 = next(work.get_definitions("module1"))
        inst_m1_1 = next(topModule.get_instances("inst_m1_1"))
        # p, c = topModule.combine_ports("mergedPort", list(topModule.get_ports(
        #         filter=lambda x: "in" in x.name)))
        # for eachI in topModule.get_instances(recursive=True):
        #     if "SDN_VERILOG_" in eachI.name:
        #         print([p.port.name for p in eachI.pins.keys()])

        # print([p.port.name for p in next(topModule.get_cables("in2")).wires[0].pins])
        # topModule.OptWires()
        # topModule.OptInstances(checkOutputs=False)
        newdef = work.create_top_wrapper("fpga_top", "fpga_core_uut")
        for eachPort in newdef.ports:
            eachPort.name = eachPort.name.upper()
        print(netlist.top_instance.name)


    resultFile = f"_{filename}_test"
    sdn.compose(netlist, os.path.join(dir_path,  f"_{resultFile}.v"),
                        write_blackbox=False)
    sdn.compose(netlist, os.path.join(dir_path, "render", f"{resultFile}.html"),
                        write_blackbox=False)

