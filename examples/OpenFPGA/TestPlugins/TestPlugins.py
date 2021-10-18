import os
import spydrnet as sdn
import logging
from io import StringIO
from spydrnet.parsers.verilog.tokenizer import *
from spydrnet.composers.html.composer import HTMLComposer


logger = logging.getLogger(__name__)
FORMAT = "%(levelname)5s (%(lineno)4s) - %(message)s"

logging.basicConfig(level=logging.INFO, format=FORMAT)

dir_path = os.path.dirname(os.path.realpath(__file__))
netlist = sdn.parse(os.path.join(dir_path, "hierDesign.v"))


# work = next(netlist.get_libraries("work"))
# topModule = next(work.get_definitions("top"))

# composer = HTMLComposer()
# composer.depth = 1
# composer.run(netlist, file_out=os.path.join(dir_path, "_result.html"))
