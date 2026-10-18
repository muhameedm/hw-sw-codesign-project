#!/bin/bash
set -e
echo "Running Float Baseline vs Optimized Benchmark..."
python3 bm_float/run_benchmark.py --values 3 -w 1 -o /tmp/flt_orig.json
python3 opt_float/run_benchmark.py --values 3 -w 1 -o /tmp/flt_opt.json
python3 -m pyperf compare_to /tmp/flt_orig.json /tmp/flt_opt.json
