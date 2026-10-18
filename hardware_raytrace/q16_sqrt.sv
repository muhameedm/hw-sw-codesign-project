`timescale 1ns / 1ps

module q16_sqrt #(
    parameter WIDTH = 32,
    parameter FRAC  = 16
)(
    input  logic                     clk,
    input  logic                     rst_n,
    input  logic                     in_valid,
    input  logic signed [WIDTH-1:0]  radicand,
    output logic                     out_valid,
    output logic signed [WIDTH-1:0]  root
);

    // Radicand is Q16.16. Shifted left by FRAC gives 48-bit domain for standard integer square root.
    logic [47:0] a_reg;
    logic [23:0] q_reg;
    logic [25:0] rem_reg;
    logic [4:0]  count;
    logic        busy;

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            busy      <= 1'b0;
            out_valid <= 1'b0;
            root      <= '0;
            count     <= '0;
        end else if (in_valid && !busy) begin
            if (radicand <= 0) begin
                root      <= '0;
                out_valid <= 1'b1;
            end else begin
                a_reg     <= {radicand, 16'b0};
                q_reg     <= '0;
                rem_reg   <= '0;
                count     <= 5'd24;
                busy      <= 1'b1;
                out_valid <= 1'b0;
            end
        end else if (busy) begin
            logic [25:0] trial_rem;
            logic [25:0] next_rem;
            logic [23:0] next_q;

            trial_rem = (rem_reg << 2) | a_reg[47:46];
            if (trial_rem >= ((q_reg << 2) | 1'b1)) begin
                next_rem = trial_rem - ((q_reg << 2) | 1'b1);
                next_q   = (q_reg << 1) | 1'b1;
            end else begin
                next_rem = trial_rem;
                next_q   = (q_reg << 1);
            end

            a_reg   <= a_reg << 2;
            rem_reg <= next_rem;
            q_reg   <= next_q;

            if (count == 5'd1) begin
                busy      <= 1'b0;
                out_valid <= 1'b1;
                root      <= {8'b0, next_q}; // Q16.16 format
            end else begin
                count <= count - 1'b1;
            end
        end else begin
            out_valid <= 1'b0;
        end
    end

endmodule
