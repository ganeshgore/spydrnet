
(* WIDTH = 200, HEIGHT = 340 *)
(* in1_SIDE = "left", in1_OFFSET = 20 *)
(* in2_SIDE = "left", in2_OFFSET = 100 *)
(* out1_SIDE = "right", out1_OFFSET = 40 *)
module top
(
    in1,
    in2,
    out1,
);

    input in1;
    input in2;
    output out1;

    wire out;

    (* LOC_X = 50, LOC_Y = 50 *)
    module1 inst_m1_1
    (
        .A(in1),
        .B(in1),
        .D(in2),
        .C(in2),
        .Q(out)
    );

    (* LOC_X = 50, LOC_Y = 180 *)
    module1 inst_m1_2
    (
        .A(in2),
        .B(in2),
        .D(in1),
        .C(out),
        .Q(out1)
    );

endmodule


(* WIDTH = 100, HEIGHT = 100 *)
(* A_SIDE = "left", A_OFFSET = 20 *)
(* B_SIDE = "left", B_OFFSET = 40 *)
(* C_SIDE = "left", C_OFFSET = 60 *)
(* D_SIDE = "left", D_OFFSET = 80 *)
(* Q_SIDE = "right", Q_OFFSET = 50 *)
module module1
(
    A,
    B,
    C,
    D,
    Q
);

    input A;
    input B;
    input D;
    input C;
    output Q;

    (* LOC_X = 20, LOC_Y = 20 *)
    AND2 AND2_1 (.AA_A(A), .AA_B(B), .AA_C(C), .AA_D(D), .AA_Q(Q));

endmodule



(* WIDTH = 50, HEIGHT = 50 *)
(* AA_A_SIDE = "left", AA_A_OFFSET = 5 *)
(* AA_B_SIDE = "left", AA_B_OFFSET = 10 *)
(* AA_C_SIDE = "left", AA_C_OFFSET = 15 *)
(* AA_D_SIDE = "left", AA_D_OFFSET = 20 *)
(* AA_Q_SIDE = "right", AA_Q_OFFSET = 10 *)
module AND2
(
    AA_A,
    AA_B,
    AA_C,
    AA_D,
    AA_Q

);

input AA_A;
input AA_B;
input AA_C;
input AA_D;
output AA_Q;


endmodule
