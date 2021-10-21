import os
import spydrnet as sdn
import logging
from io import StringIO
from spydrnet.parsers.verilog.tokenizer import *
from spydrnet.composers.html.composer import HTMLComposer
from spydrnet.util.hierarchical_reference import HRef

logger = logging.getLogger(__name__)
FORMAT = "%(levelname)5s (%(lineno)4s) - %(message)s"

logging.basicConfig(level=logging.INFO, format=FORMAT)

dir_path = os.path.dirname(os.path.realpath(__file__))
netlist = sdn.parse(os.path.join(dir_path, "hierDesign.v"))


library = next(netlist.get_libraries("work"))
topModule = next(library.get_definitions("top"))

# library.create_top_wrapper(name="wrapper", inst_name="warpper_0")

# props = [attribute for attribute in dir(topModule) if \
#             not callable(getattr(topModule, attribute)) and \
#                 attribute.startswith('href_') is True]
# print(props)
mod2_1 = next(netlist.get_hinstances())
# print(next(mod2_1.get_hinstances()))
# print(type(mod2_1))
# print(isinstance(mod2_1, HRef))
# print(dir(mod2_1))
mod2_1.href_get_x
mod2_1.item.href_get_x
# print(type(mod2_1.href_get_x))
# print(mod2_1.pp)
# print(type(mod2_1.item))

sdn.compose(netlist, os.path.join(dir_path, "_hierDesign.v"))