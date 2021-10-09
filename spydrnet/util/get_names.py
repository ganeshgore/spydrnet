import logging
from collections.abc import Iterable
from spydrnet.ir.cable import Cable
from spydrnet.ir.port import Port
from spydrnet.ir.definition import Definition
from spydrnet.ir.instance import Instance

logger = logging.getLogger('spydrnet_logs')

def get_names(objects):
    names = []
    if not isinstance(objects, Iterable):
        objects = tuple(objects)
    for each in objects:
        if isinstance(each, (Cable, Port, Definition, Instance)):
            names.append(each.name)
        else:
            logger.warn(f"Skipping unsupport object {type(each)}")
    return names