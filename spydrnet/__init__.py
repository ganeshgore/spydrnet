"""
SpyDrNet
========

SpyDrNet is an EDA tool for analyzing and transforming netlists.

See https://byuccl.github.io/spydrnet for more details.
"""

import importlib
import pkgutil
import pathlib
import sys
import os

discovered_plugins = {
    name: importlib.import_module(name)
    for finder, name, ispkg
    in pkgutil.iter_modules()
    if name.startswith('spydrnet_')
}
print("Installed Plugins", discovered_plugins.keys())

def get_active_plugins():
    active_plugins = {}
    config_file = os.path.join(pathlib.Path.home(), ".spydrnet")
    if os.path.isfile(config_file):
        for plugin in open(config_file, "r").read().split():
            if discovered_plugins.get(plugin, None):
                active_plugins.update({plugin: discovered_plugins[plugin]})
            else:
                print("Plugin %s is not installed " % plugin)
    else:
        with open(config_file, "w") as fp:
            fp.write("\n".join(discovered_plugins.keys()))
        active_plugins.update(discovered_plugins)
    return active_plugins


print("Active Plugins", get_active_plugins().keys())

# Release data
from spydrnet import release

__author__ = '%s <%s>\n%s <%s>\n%s <%s>' % \
    (release.authors['Keller'] + release.authors['Skouson'] +
        release.authors['Wirthlin'])
__license__ = release.license

__date__ = release.date
__version__ = release.version
__release__ = release.release

from spydrnet.ir import *
from spydrnet.util.hierarchical_reference import HRef

OUT = Port.Direction.OUT
IN = Port.Direction.IN
INOUT = Port.Direction.INOUT
UNDEFINED = Port.Direction.UNDEFINED

from spydrnet.util.selection import INSIDE, OUTSIDE, BOTH, ALL

from spydrnet.testing.test import run as test
from spydrnet.parsers import parse
from spydrnet.composers import compose

from spydrnet.plugins import namespace_manager
from spydrnet.util import get_netlists, get_libraries, get_definitions, get_ports, get_cables, get_instances,\
    get_wires, get_pins
from spydrnet.util import get_hinstances, get_hports, get_hpins, get_hcables, get_hwires

import os
base_dir = os.path.dirname(os.path.abspath(__file__))

import glob
example_netlist_names = list()
for filename in glob.glob(os.path.join(base_dir, 'support_files', 'EDIF_netlists', "*")):
    basename = os.path.basename(filename)
    example_netlist_names.append(basename[:basename.index('.')])
example_netlist_names.sort()

# logger for the module
import logging
import sys
LOG_FORMAT = "%(levelname)5s %(filename)s:%(lineno)s (%(threadName)10s) - %(message)s"

logger = logging.getLogger('spydrnet_logs')
logger.setLevel(logging.DEBUG)

stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setLevel(logging.INFO)
stream_handler.setFormatter(logging.Formatter(LOG_FORMAT))
logger.addHandler(stream_handler)

def enable_file_logging(LOG_LEVEL=None):
    LOG_LEVEL = LOG_LEVEL or "INFO"
    file_handler = logging.FileHandler("_spydrnet.log", mode='w')
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT))
    file_handler.setLevel(eval(f"logging.{LOG_LEVEL}"))
    logger.addHandler(file_handler)
    return file_handler

# from spydrnet.util.shell import launch_shell
# from spydrnet.util.renders import start_gui
# from spydrnet.util.get_names import get_names
def load_example_netlist_by_name(name):
    assert name in example_netlist_names, "Example netlist not found"
    return parse(os.path.join(base_dir, 'support_files', 'EDIF_netlists', name + ".edf.zip"))
