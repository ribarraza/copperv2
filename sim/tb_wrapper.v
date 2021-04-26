`timescale 1ns/1ps
`include "copperv_h.v"

module tb_wrapper();
    // copperv inputs
    reg clock;
    reg reset;
    reg bus_dr_data_valid;
    reg bus_dr_addr_ready;
    reg bus_dw_req_ready;
    reg bus_dw_resp_valid;
    reg [`BUS_WIDTH-1:0] bus_dr_data_bits;
    reg bus_ir_data_valid;
    reg bus_ir_addr_ready;
    reg [`BUS_WIDTH-1:0] bus_ir_data_bits;
    reg [`BUS_RESP_WIDTH-1:0] bus_dw_resp_bits;
    // copperv outputs
    wire bus_dr_data_ready;
    wire bus_dr_addr_valid;
    wire bus_dw_req_valid;
    wire bus_dw_resp_ready;
    wire [`BUS_WIDTH-1:0] bus_dr_addr_bits;
    wire [`BUS_WIDTH-1:0] bus_dw_req_bits_data;
    wire [`BUS_WIDTH-1:0] bus_dw_req_bits_addr;
    wire [(`BUS_WIDTH/8)-1:0] bus_dw_req_bits_strobe;
    wire bus_ir_data_ready;
    wire bus_ir_addr_valid;
    wire [`BUS_WIDTH-1:0] bus_ir_addr_bits;

    `ifndef DUT_COPPERV1
    Copperv2 dut (
        .clock(clock),
        .reset(reset),
        .bus_dr_data_valid(bus_dr_data_valid),
        .bus_dr_addr_ready(bus_dr_addr_ready),
        .bus_dw_req_ready(bus_dw_req_ready),
        .bus_dw_resp_valid(bus_dw_resp_valid),
        .bus_dr_data_bits(bus_dr_data_bits),
        .bus_ir_data_valid(bus_ir_data_valid),
        .bus_ir_addr_ready(bus_ir_addr_ready),
        .bus_ir_data_bits(bus_ir_data_bits),
        .bus_dw_resp_bits(bus_dw_resp_bits),
        .bus_dr_data_ready(bus_dr_data_ready),
        .bus_dr_addr_valid(bus_dr_addr_valid),
        .bus_dw_req_valid(bus_dw_req_valid),
        .bus_dw_resp_ready(bus_dw_resp_ready),
        .bus_dr_addr_bits(bus_dr_addr_bits),
        .bus_dw_req_bits_data(bus_dw_req_bits_data),
        .bus_dw_req_bits_addr(bus_dw_req_bits_addr),
        .bus_dw_req_bits_strobe(bus_dw_req_bits_strobe),
        .bus_ir_data_ready(bus_ir_data_ready),
        .bus_ir_addr_valid(bus_ir_addr_valid),
        .bus_ir_addr_bits(bus_ir_addr_bits)
    );
    `else
    copperv dut (
        .clk(clock),
        .rst(reset),
        .dr_data_valid(bus_dr_data_valid),
        .dr_addr_ready(bus_dr_addr_ready),
        .dw_data_addr_ready(bus_dw_req_ready),
        .dw_resp_valid(bus_dw_resp_valid),
        .dr_data(bus_dr_data_bits),
        .ir_data_valid(bus_ir_data_valid),
        .ir_addr_ready(bus_ir_addr_ready),
        .ir_data(bus_ir_data_bits),
        .dw_resp(bus_dw_resp_bits),
        .dr_data_ready(bus_dr_data_ready),
        .dr_addr_valid(bus_dr_addr_valid),
        .dw_data_addr_valid(bus_dw_req_valid),
        .dw_resp_ready(bus_dw_resp_ready),
        .dr_addr(bus_dr_addr_bits),
        .dw_data(bus_dw_req_bits_data),
        .dw_addr(bus_dw_req_bits_addr),
        .dw_strobe(bus_dw_req_bits_strobe),
        .ir_data_ready(bus_ir_data_ready),
        .ir_addr_valid(bus_ir_addr_valid),
        .ir_addr(bus_ir_addr_bits)
    );
    `endif

    initial begin
        `ifndef DUT_COPPERV1
        $dumpfile ("copperv2.vcd");
        `else
        $dumpfile ("copperv1.vcd");
        `endif
        $dumpvars(0, tb_wrapper);
        #1;
    end
endmodule
