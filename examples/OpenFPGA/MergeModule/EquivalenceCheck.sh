#!/bin/bash
yosys -p "read_verilog _result_equiv.v;
read_verilog hierDesign.v;
equiv_make top top_eq equiv;
hierarchy -top equiv;
clean ­purge;
show -format dot ;
equiv_simple;
equiv_status ­-assert"
