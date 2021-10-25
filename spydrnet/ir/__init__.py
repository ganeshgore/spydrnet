
import typing
if typing.TYPE_CHECKING:
    from spydrnet.ir.element import Element
    from spydrnet.ir.first_class_element import FirstClassElement
    from spydrnet.ir.netlist import Netlist
    from spydrnet.ir.library import Library
    from spydrnet.ir.definition import Definition
    from spydrnet.ir.port import Port
    from spydrnet.ir.cable import Cable
    from spydrnet.ir.wire import Wire
    from spydrnet.ir.instance import Instance
    from spydrnet.ir.innerpin import InnerPin
    from spydrnet.ir.outerpin import OuterPin
    from spydrnet.ir.bundle import Bundle
    from spydrnet.ir.pin import Pin

# Following section will extend all the classes imported in this file
import importlib
from spydrnet import get_active_plugins
print("Loading IR Module")
for name, plugin in get_active_plugins().items():
    print(f"name {name}")
    # ext = importlib.import_module("%s.ir" % name)
    # ImportedModules = [attribute for attribute in dir(ext) if
    #                    callable(getattr(ext, attribute)) and
    #                    attribute.startswith('__') is False]
    # print(ImportedModules)

    # for eachModule in ImportedModules:
    #     if eachModule in globals():
    #         pluginModule = ext.__dict__[eachModule]
    #         baseModule = globals()[eachModule]
    #         print(f"Extending {baseModule} with {pluginModule}")
    #         # locals()[eachModule] = type(eachModule, (baseModule,), pluginModule.__dict__.copy())
    for filename, eachModule in [('element', 'Element'), ('first_class_element', 'FirstClassElement'), ('bundle', 'Bundle'), ('pin', 'Pin'), ('innerpin', 'InnerPin'), ('outerpin', 'OuterPin'), ('port', 'Port'), ('wire', 'Wire'), ('cable', 'Cable'), ('instance', 'Instance'), ('definition', 'Definition'), ('library', 'Library'), ('netlist', 'Netlist'), ]:

        # cls = globals()[eachModule+"Base"]
        cls = getattr(importlib.import_module(
            "spydrnet.ir."+filename), eachModule)
        locals()[eachModule] = type(cls.__name__, (cls,), {})
        print(f"Adding {eachModule}Base")
        if eachModule in ["Definition", "Cable"]:
            ext_cls = getattr(importlib.import_module(
                "%s.ir.%s" % (name, filename)), eachModule)
            print(f"Extending {cls} with {ext_cls}")
            cls_bases = (ext_cls, cls)
            locals()[eachModule] = type(cls.__name__, cls_bases, {})
        print(f"Adding {eachModule}")
