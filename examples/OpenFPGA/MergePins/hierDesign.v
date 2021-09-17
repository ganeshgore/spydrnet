// Sampel netlist for Hierarchical design experiements

// +----------------------------------------------
// |                                        TOP  |
// |     +-------------+    +-------------+      |
// +-----+             |    |             |      |
// | n1| |             | +--+             |   n3 |
// |   | |    MOD1_1   +-+  |    MOD1_2   +------+
// |   +-+             | +--+             |      |
// |     |             |    |             |      |
// |     +-------------+    +-------------+      |
// |                                             |
// |---------------------------------------------+



module top
(
    in1,
    in2,
    out1,
);

    input in1;
    input in2;
    output out1;

    wire n2;

    module1 inst_m1_1
    (
        .A(in1),
        .B(in1),
        .C(in2),
        .Q(n2)
    );
    module1 inst_m1_2
    (
        .A(n2),
        .B(n2),
        .C(in2),
        .Q(out1)
    );

endmodule

module module1
(
    A,
    B,
    C,
    Q
);

    input A;
    input B;
    input C;
    output Q;



    AND2 AND2_1 (.AA_A(A), .AA_B(B), .AA_Q(Q));

endmodule


`celldefine
module AND2(
    AA_A,
    AA_B,
    AA_Q

);
input AA_A;
input AA_B;
output AA_Q;

endmodule
`endcelldefine