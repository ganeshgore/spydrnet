// Sampel netlist for Hierarchical design experiements

//  ┌─────────────────────────────────────────────┐
//  │             n2                              │
//  ├─────────────────────┐                       │
//  │                     │                       │
//  │     ┌─────────────┐ │  ┌─────────────┐      │
//  ├─────┤             │ │  │             │      │
//  │ n1  │             │ └──┤             │   n3 │
//  │     │    MOD1     │    │    MOD2     ├──────┤
//  │     │             ├────┤             │      │
//  │     │             │ ┌──┤             │      │
//  │     └─────────────┘ │  └─────────────┘      │
//  │         bus1        │                 TOP   │
//  ├─────────────────────┘                       │
//  └─────────────────────────────────────────────┘


module top
(
    n1,
    n2,
    n3,
    bus1,
);

    input n1;
    input n2;
    input [1:0]bus1;
    output n3;

    wire n1;
    wire n2;
    wire n3;
    wire n4;
    wire n5;
    wire [1:0]bus1;

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

    MOD1 mod1_2
    (
        .A(n1),
        .Q(n5)
    );
    MOD2 mod2_2
    (
        .A(n2),
        .B(n5),
        .bus1(bus1),
        .Q(n3)
    );

    MOD3 MOD3_1 (.A(n2), .B(n5));

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

endmodule

module MOD2
(
    A,
    B,
    Q,
    bus1
);

    input A;
    input B;
    input [1:0]bus1;
    output Q;

    wire A;
    wire B;
    wire Q;
    wire [1:0]bus1;

endmodule

