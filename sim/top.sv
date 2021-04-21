module top (
        input clock,
        input reset
    );
    copperv2_bfm bfm();
    Copperv2 DUT (
        .clock(clock),
        .reset(reset),
        .bus_ir_addr_ready(bfm.bus_ir_addr_ready),
        .bus_ir_addr_valid(bfm.bus_ir_addr_valid),
        .bus_ir_addr_bits(bfm.bus_ir_addr_bits),
        .bus_ir_data_ready(bfm.bus_ir_data_ready),
        .bus_ir_data_valid(bfm.bus_ir_data_valid),
        .bus_ir_data_bits(bfm.bus_ir_data_bits),
        .bus_dr_addr_ready(bfm.bus_dr_addr_ready),
        .bus_dr_addr_valid(bfm.bus_dr_addr_valid),
        .bus_dr_addr_bits(bfm.bus_dr_addr_bits),
        .bus_dr_data_ready(bfm.bus_dr_data_ready),
        .bus_dr_data_valid(bfm.bus_dr_data_valid),
        .bus_dr_data_bits(bfm.bus_dr_data_bits),
        .bus_dw_req_ready(bfm.bus_dw_req_ready),
        .bus_dw_req_valid(bfm.bus_dw_req_valid),
        .bus_dw_req_bits_data(bfm.bus_dw_req_bits_data),
        .bus_dw_req_bits_addr(bfm.bus_dw_req_bits_addr),
        .bus_dw_req_bits_strobe(bfm.bus_dw_req_bits_strobe),
        .bus_dw_resp_ready(bfm.bus_dw_resp_ready),
        .bus_dw_resp_valid(bfm.bus_dw_resp_valid),
        .bus_dw_resp_bits(bfm.bus_dw_resp_bits)
    );
endmodule : top
