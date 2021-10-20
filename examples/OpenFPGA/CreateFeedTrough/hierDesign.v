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

endmodule

module MOD2
(
    A,
    B,
    Q,
    [1:0]bus1
);

    input A;
    input B;
    input [1:0]bus1;
    output Q;

    wire A;
    wire B;
    wire Q;
    wire bus1;

endmodule
