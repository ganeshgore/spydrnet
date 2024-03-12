from pathlib import Path
from spydrnet.composers.edif.composer import ComposeEdif
from spydrnet.composers.verilog.composer import Composer as VerilogComposer
from spydrnet.composers.eblif.eblif_composer import EBLIFComposer


def compose(
    netlist,
    filename,
    *arg,
    **kwargs
):
    """To compose a file into a netlist format"""
    extension = Path(filename).suffix
    extension_lower = extension.lower()
    if extension_lower in {".edf", ".edif"}:
        composer = ComposeEdif(*arg, **kwargs)
        if netlist.name is None:
            raise Exception("netlist.name undefined")
        composer.run(netlist, filename)
    elif extension_lower in [".v", ".vh", ".vm"]:
        composer = VerilogComposer(*arg, **kwargs)
        composer.run(netlist, file_out=filename)
    elif extension_lower in [".eblif", ".blif"]:
        composer = EBLIFComposer(*arg, **kwargs)
        composer.run(netlist, filename)
    else:
        raise RuntimeError("Extension {} not recognized.".format(extension))
