//Generated from netlist by SpyDrNet
//netlist name: SDN_VERILOG_NETLIST_top

module top
(
    n1,
    n2,
    n3,
    bus1
);

    input n1;
    input n2;
    output n3;
    input [1:0]bus1;

    wire n1;
    wire n2;
    wire n3;
    wire [1:0]bus1;
    wire n4;

    MOD1 mod1_1
    (
        .A(n1),
        .Q(n4)
    );
    MOD2 mod2_1
    (
        .A(n2),
        .B(n4),
        .bus1(bus1),
        .Q(n3)
    );
endmodule

module MOD1
(
    A,
    Q
);

    input A;
    output Q;

    wire A;
    wire Q;

    AND and_0
    (
        .A(n1),
        .Q(n4)
    );

endmodule

module AND
(
    A,
    Q
);

    input A;
    output Q;

    wire A;
    wire Q;

endmodule

module MOD2
(
    A,
    B,
    bus1,
    Q
);

    input A;
    input B;
    input [1:0]bus1;
    output Q;

    wire A;
    wire B;
    wire Q;
    wire [1:0]bus1;

    AND and_1
    (
        .A(n1),
        .Q(n4)
    );

endmodule

