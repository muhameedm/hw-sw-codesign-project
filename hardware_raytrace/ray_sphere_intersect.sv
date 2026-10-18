`timescale 1ns / 1ps

module ray_sphere_intersect (
    input  logic                     clk,
    input  logic                     rst_n,
    input  logic                     in_valid,
    output logic                     in_ready,

    // Sphere definition: Center (cx, cy, cz) and Radius R in Q16.16
    input  logic signed [31:0]       cx, cy, cz,
    input  logic signed [31:0]       radius,

    // Ray definition: Origin (px, py, pz) and Direction (dx, dy, dz) in Q16.16
    input  logic signed [31:0]       px, py, pz,
    input  logic signed [31:0]       dx, dy, dz,

    output logic                     out_valid,
    input  logic                     out_ready,
    output logic                     hit,
    output logic signed [31:0]       t_hit // Distance t in Q16.16
);

    typedef enum logic [2:0] {
        IDLE,
        CALC_DIFF,
        CALC_DOT,
        CALC_DISC,
        SQRT_WAIT,
        EMIT
    } state_t;

    state_t state;

    // Internal vectors and scalars
    logic signed [31:0] cpx, cpy, cpz;
    logic signed [63:0] dot_v_long;
    logic signed [63:0] cp_dot_cp_long;
    logic signed [63:0] r_sq_long;
    logic signed [31:0] v_val;
    logic signed [31:0] disc;
    logic               sqrt_start;
    logic               sqrt_done;
    logic signed [31:0] sqrt_out;

    q16_sqrt u_sqrt (
        .clk(clk),
        .rst_n(rst_n),
        .in_valid(sqrt_start),
        .radicand(disc),
        .out_valid(sqrt_done),
        .root(sqrt_out)
    );

    assign in_ready = (state == IDLE);

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state      <= IDLE;
            out_valid  <= 1'b0;
            hit        <= 1'b0;
            t_hit      <= '0;
            sqrt_start <= 1'b0;
        end else begin
            case (state)
                IDLE: begin
                    out_valid <= 1'b0;
                    if (in_valid) begin
                        // cp = centre - ray.point
                        cpx   <= cx - px;
                        cpy   <= cy - py;
                        cpz   <= cz - pz;
                        state <= CALC_DOT;
                    end
                end

                CALC_DOT: begin
                    // v = cp . dir, cp_dot_cp = cp . cp, r^2
                    dot_v_long      <= (cpx * dx) + (cpy * dy) + (cpz * dz);
                    cp_dot_cp_long  <= (cpx * cpx) + (cpy * cpy) + (cpz * cpz);
                    r_sq_long       <= (radius * radius);
                    state           <= CALC_DISC;
                end

                CALC_DISC: begin
                    // Truncate Q32.32 back to Q16.16
                    logic signed [31:0] v_scaled;
                    logic signed [31:0] cp2_scaled;
                    logic signed [31:0] r2_scaled;
                    logic signed [63:0] v2_long;
                    logic signed [31:0] v2_scaled;

                    v_scaled   = dot_v_long >>> 16;
                    cp2_scaled = cp_dot_cp_long >>> 16;
                    r2_scaled  = r_sq_long >>> 16;
                    v_val      <= v_scaled;

                    v2_long    = (v_scaled * v_scaled);
                    v2_scaled  = v2_long >>> 16;

                    // discriminant = r^2 - (cp.cp - v^2)
                    disc <= r2_scaled - (cp2_scaled - v2_scaled);

                    if ((r2_scaled - (cp2_scaled - v2_scaled)) < 0) begin
                        // No real roots -> Miss
                        hit       <= 1'b0;
                        t_hit     <= '0;
                        state     <= EMIT;
                    end else begin
                        sqrt_start <= 1'b1;
                        state      <= SQRT_WAIT;
                    end
                end

                SQRT_WAIT: begin
                    sqrt_start <= 1'b0;
                    if (sqrt_done) begin
                        hit   <= 1'b1;
                        t_hit <= v_val - sqrt_out;
                        state <= EMIT;
                    end
                end

                EMIT: begin
                    out_valid <= 1'b1;
                    if (out_ready) begin
                        out_valid <= 1'b0;
                        state     <= IDLE;
                    end
                end
            endcase
        end
    end

endmodule
