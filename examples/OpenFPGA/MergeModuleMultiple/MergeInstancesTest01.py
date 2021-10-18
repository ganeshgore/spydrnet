import os
from spydrnet.ir import cable
from spydrnet.ir.port import Port
from spydrnet.ir.instance import Instance
from spydrnet.ir.definition import Definition
from spydrnet.ir.innerpin import InnerPin
from spydrnet.ir.outerpin import OuterPin
import spydrnet as sdn
import logging
import io
from spydrnet.parsers.verilog.parser import VerilogParser


logger = logging.getLogger(__name__)
FORMAT = "%(levelname)5s (%(lineno)4s) - %(message)s"


def main():
    dir_path = os.path.dirname(os.path.realpath(__file__))
    netlist = parser.netlist

    work = next(netlist.get_libraries("work"))
    topModule = next(work.get_definitions("top"))


    MOD1_1 = next(topModule.get_instances("mod1_1"))
    MOD2_1 = next(topModule.get_instances("mod2_1"))
    MOD1_2 = next(topModule.get_instances("mod1_2"))
    MOD2_2 = next(topModule.get_instances("mod2_2"))

    topModule.merge_instance([MOD1_1, MOD2_1],
                new_definition_name="merge1",
                new_instance_name="merge1_1")
    topModule.merge_instance([MOD1_2, MOD2_2],
                new_definition_name="merge2",
                new_instance_name="merge2_1")

    # Auto test Merging
    assert "merge1" in [d.name for d in work.get_definitions()], \
                "Missing merge module"
    assert "merge2" in [d.name for d in work.get_definitions()], \
                "Missing merge module"
    assert "merge1_1" in [i.name for i in topModule.children], \
                "Missing merge module instance"
    assert "merge2_1" in [i.name for i in topModule.children], \
                "Missing merge module instance"


    sdn.compose(netlist, os.path.join(dir_path, "_result.v"))

    for eachDef in work.get_definitions():
        eachDef.name += "_eq"
    sdn.compose(netlist, os.path.join(dir_path, "_result_equiv.v"))

InputModule = """
module top ( n1, n2, n3, bus1);

    input n1, n2;
    input [1:0]bus1;
    output n3;

    wire n1;
    wire n2;
    wire n3;
    wire n4;
    wire n5;
    wire [1:0]bus1;

    mod1 mod1_1 (.A(n1), .Q(n4));
    mod2 mod2_1 (.A(n2), .B(n4), .bus1(bus1), .Q(n3));

    mod1 mod1_2 (.A(n1), .Q(n5));
    mod2 mod2_2 (.A(n2), .B(n5), .bus1(bus1), .Q(n3));

endmodule

module mod1 (A, Q);
    input A;
    output Q;

    wire A;
    wire Q;

endmodule

module mod2 (A, B, Q, bus1);
    input A, B;
    input [1:0]bus1;
    output Q;

    wire A;
    wire B;
    wire Q;
    wire [1:0]bus1;

endmodule

"""

if __name__ == "__main__":
    with io.StringIO() as f:
        f.write(InputModule)
        f.seek(0)
        parser = VerilogParser.from_file_handle(f)
        parser.parse()
    main()


