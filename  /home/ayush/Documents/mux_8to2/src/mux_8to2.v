module mux_8to2 (
  input  [7:0]  data_in,
  input  [2:0]  sel,
  output [1:0]  data_out
);

  always @(*) begin
    case (sel)
      3'b000: data_out = data_in[1:0];
      3'b001: data_out = data_in[3:2];
      3'b010: data_out = data_in[5:4];
      3'b011: data_out = data_in[7:6];
      3'b100: data_out = data_in[1:0];
      3'b101: data_out = data_in[3:2];
      3'b110: data_out = data_in[5:4];
      3'b111: data_out = data_in[7:6];
      default: data_out = 2'b00;
    endcase
  end

endmodule