import os
import glob
import logging
import difflib
import spydrnet as sdn
from spydrnet.util.get_floorplan import FloorPlanViz


logger = sdn.logger
ll = sdn.enable_file_logging("DEBUG")


dir_path = os.path.dirname(os.path.realpath(__file__))




for eachFile in glob.glob('./source/hier[a-zA-Z]*.v'):
    filename = os.path.splitext(os.path.basename(eachFile))[0]

    logger.debug("===========================================")
    logger.info(f"Reading design {eachFile}")
    netlist = sdn.parse(os.path.join(dir_path, eachFile))

    work = next(netlist.get_libraries("work"))
    topModule = next(work.get_definitions("top"))
    module1 = next(work.get_definitions("module1"))


    m1_1 = next(work.get_instances("inst_m1_1"))
    m1_2 = next(work.get_instances("inst_m1_2"))

    resultFile = f"_{filename}_test"
    sdn.compose(netlist, os.path.join(dir_path, "result", f"{resultFile}.v"),
                        write_blackbox=False)
    sdn.compose(netlist, os.path.join(dir_path, "render", f"{resultFile}.html"),
                        write_blackbox=False)


    # module1._data["VERILOG.InlineConstraints"] = {}
    fp = FloorPlanViz(module1)
    fp.compose()
    dwg = fp.get_svg()
    dwg.saveas("_sample.svg", pretty=True, indent=4)


    # gui = sdn.start_gui()
    # sdn.launch_shell()
    # gui.show_floorplan(topModule)