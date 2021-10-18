

module top
(
    in1,
    in2,
    out1,
);

    input [1:0]in1;
    input in2;
    output out1;

    wire out;
    module1 inst_m1_1
    (
        .A(in1),
        .B(in1),
        .D(in2),
        .C(in2),
        .Q(out)
    );
    module1 inst_m1_2
    (
        .A(in2),
        .B(in2),
        .D(in1),
        .C(out),
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
    input B;
    input D;
    input C;
    output Q;

    // AND2 AND2_1 (.AA_A(A), .AA_B(B), .AA_C(C), .AA_D(D), .AA_Q(Q));

endmodule