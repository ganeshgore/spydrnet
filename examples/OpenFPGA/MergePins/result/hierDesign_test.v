//Generated from netlist by SpyDrNet
//netlist name: SDN_VERILOG_NETLIST_top
module top
(
    in1,
    in2,
    out1
);

    input in1;
    input in2;
    output out1;

    wire in1;
    wire in2;
    wire out1;
    wire out;

    module1 inst_m1_1
    (
        .A(in1),
        .D(in2),
        .C(in2),
        .Q(out)
    );
    module1 inst_m1_2
    (
        .A(in2),
        .D(in1),
        .C(out),
        .Q(out1)
    );
endmodule

module module1
(
    A,
    D,
    C,
    Q
);

    input A;
    input D;
    input C;
    output Q;

    wire A;
    wire C;
    wire D;
    wire Q;

    AND2 AND2_1
    (
        .AA_A(A),
        .AA_B(A),
        .AA_C(C),
        .AA_D(D),
        .AA_Q(Q)
    );
endmodule

