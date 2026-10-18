#!/bin/bash
set -e
echo "Running Raytrace Baseline vs Optimized Benchmark..."
python3 bm_raytrace/run_benchmark.py --values 3 -w 1 -o /tmp/ray_orig.json
python3 opt_raytrace/run_benchmark.py --values 3 -w 1 -o /tmp/ray_opt.json
python3 -m pyperf compare_to /tmp/ray_orig.json /tmp/ray_opt.json
echo "Simulating Hardware Accelerator..."
cd hardware_raytrace
iverilog -g2012 -o sim_ray_sphere q16_sqrt.sv ray_sphere_intersect.sv tb_ray_sphere.sv
vvp sim_ray_sphere
