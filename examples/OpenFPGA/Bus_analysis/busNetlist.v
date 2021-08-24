// Simple netlist having bus connections to test
module top
(
    ANet,
    Ynet
);

    input [3:0]ANet;
    output Ynet;

    wire [3:0]ANet;
    wire Ynet;
    wire Q1;
    wire Q2;

    AND2 and2_1
    (
        .A(ANet[0]),
        .B(ANet[1]),
        .Q(Q1)
    );
    AND2 and2_2
    (
        .A(ANet[2]),
        .B(ANet[3]),
        .Q(Q2)
    );
    OR2 or2_1
    (
        .A({Q1, Q2}),
        .B({Q1, Q2}),
        .Q(Ynet)
    );
endmodule

module AND2
(
    A,
    B,
    Q
);

    input A;
    input B;
    output Q;

    wire A;
    wire B;
    wire Q;

endmodule

module OR2
(
    A,
    B,
    Q
);

    input [1:0]A;
    input [1:0]B;
    output Q;

    wire [1:0]A;
    wire [1:0]B;
    wire Q;

endmodule

