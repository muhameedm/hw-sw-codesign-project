`timescale 1ns / 1ps

module tb_ray_sphere;

    logic clk;
    logic rst_n;
    logic in_valid;
    logic in_ready;
    logic signed [31:0] cx, cy, cz, radius;
    logic signed [31:0] px, py, pz, dx, dy, dz;
    logic out_valid;
    logic out_ready;
    logic hit;
    logic signed [31:0] t_hit;

    ray_sphere_intersect dut (.*);

    always #5 clk = ~clk;

    initial begin
        clk       = 0;
        rst_n     = 0;
        in_valid  = 0;
        out_ready = 1;
        #20;
        rst_n     = 1;
        #10;

        // Test 1: Ray hitting sphere centered at (0, 0, 10) with Radius = 2
        // Ray from (0, 0, 0) pointing in +Z direction (0, 0, 1)
        // Expected hit at t = 10 - 2 = 8.0 (Q16.16 = 8 * 65536 = 524288)
        @(posedge clk);
        cx     = 32'sd0;
        cy     = 32'sd0;
        cz     = 32'sd10 <<< 16;
        radius = 32'sd2 <<< 16;
        px     = 32'sd0;
        py     = 32'sd0;
        pz     = 32'sd0;
        dx     = 32'sd0;
        dy     = 32'sd0;
        dz     = 32'sd1 <<< 16;
        in_valid = 1;

        @(posedge clk);
        in_valid = 0;

        @(posedge out_valid);
        #1;
        if (hit && (t_hit >= (8 <<< 16) - 100) && (t_hit <= (8 <<< 16) + 100)) begin
            $display("TEST 1 PASSED: Direct Hit at t = %0f", $itor(t_hit)/65536.0);
        end else begin
            $display("TEST 1 FAILED: hit=%0d, t=%0d", hit, t_hit);
        end

        // Test 2: Ray completely missing the sphere
        // Sphere at (10, 10, 10), Ray along +Z
        @(posedge clk);
        cx     = 32'sd10 <<< 16;
        cy     = 32'sd10 <<< 16;
        cz     = 32'sd10 <<< 16;
        radius = 32'sd2 <<< 16;
        in_valid = 1;

        @(posedge clk);
        in_valid = 0;

        @(posedge out_valid);
        #1;
        if (!hit) begin
            $display("TEST 2 PASSED: Correctly detected Miss");
        end else begin
            $display("TEST 2 FAILED: Expected Miss but got Hit");
        end

        $display("ALL HARDWARE TESTS COMPLETED.");
        $finish;
    end

endmodule
