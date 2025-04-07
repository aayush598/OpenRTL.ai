`timescale 1ns / 1ps

module mux_8to2_tb;

    // Inputs
    reg [7:0] data_in;
    reg [2:0] select;

    // Output
    wire [1:0] data_out;

    // Instantiate the Unit Under Test (UUT)
    mux_8to2 uut (
        .data_in(data_in),
        .select(select),
        .data_out(data_out)
    );

    // Stimulus
    initial begin
        // Initialize Inputs
        data_in = 8'b00000000;
        select = 3'b000;
        #10;

        // Test cases
        data_in = 8'b10101010;
        select = 3'b000;
        #10;

        data_in = 8'b11110000;
        select = 3'b001;
        #10;

        data_in = 8'b00001111;
        select = 3'b010;
        #10;

        data_in = 8'b10001000;
        select = 3'b011;
        #10;

        data_in = 8'b01010101;
        select = 3'b100;
        #10;

        data_in = 8'b11001100;
        select = 3'b101;
        #10;

        data_in = 8'b00110011;
        select = 3'b110;
        #10;

        data_in = 8'b11111111;
        select = 3'b111;
        #10;

        // Add more test cases as needed

        $finish;
    end

    // Monitor
    initial begin
        $monitor ("Time=%t, data_in=%b, select=%b, data_out=%b", $time, data_in, select, data_out);
    end

endmodule