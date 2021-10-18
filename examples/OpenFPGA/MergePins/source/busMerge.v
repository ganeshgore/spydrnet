

module top
(
    in1,
    in2,
    out1,
);

    input [1:0]in1;
    input [1:0]in2;
    output [1:0]out1;

    wire [1:0]out;

    module1 inst_m1_1
    (
        .A(in1),
        .B(in1),
        .C(in2),
        .D(in1),
        .Q(out)
    );
    module1 inst_m1_2
    (
        .A(in1),
        .B(in1),
        .C(out),
        .D(in1),
        .Q(out1)
    );

endmodule


module module1
(
    A,
    B,
    C,
    D,
    Q
);

    input [1:0]A;
    input [1:0]B;
    input [1:0]C;
    input [1:0]D;
    output [1:0]Q;

    AND2 AND2( .A(A), .B(B), .C(C), .D(D),  .Q(Q));

endmodule