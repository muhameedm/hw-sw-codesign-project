#!/bin/bash
# Full raytrace flow: setup, profiling, flame graphs, comparison, HW simulation.
# Run inside the course QEMU VM from the repository root.
set -euo pipefail
cd "$(dirname "$0")"

FLAMEGRAPH_DIR="${FLAMEGRAPH_DIR:-/root/FlameGraph}"
RESULTS=results/raytrace
mkdir -p "$RESULTS"

echo "== Environment setup =="
python3 -c 'import pyperf' 2>/dev/null || python3 -m pip install pyperf
command -v perf >/dev/null || { echo "perf is required"; exit 1; }
command -v iverilog >/dev/null || apt-get install -y iverilog
[ -d "$FLAMEGRAPH_DIR" ] || git clone https://github.com/brendangregg/FlameGraph "$FLAMEGRAPH_DIR"

flamegraph() {  # name, benchmark path
    perf record -F 999 -g -o "$RESULTS/$1.perf" -- python3 "$2" --values 1 -w 0
    perf report --stdio -i "$RESULTS/$1.perf" > "$RESULTS/$1_perf_report.txt"
    perf script -i "$RESULTS/$1.perf" \
        | "$FLAMEGRAPH_DIR/stackcollapse-perf.pl" \
        | "$FLAMEGRAPH_DIR/flamegraph.pl" > "$RESULTS/$1.svg"
}

echo "== Profiling and flame graphs =="
flamegraph raytrace_orig bm_raytrace/run_benchmark.py
flamegraph raytrace_opt opt_raytrace/run_benchmark.py

echo "== Baseline vs optimized =="
python3 bm_raytrace/run_benchmark.py --values 3 -w 1 -o "$RESULTS/raytrace_orig.json"
python3 opt_raytrace/run_benchmark.py --values 3 -w 1 -o "$RESULTS/raytrace_opt.json"
python3 -m pyperf compare_to "$RESULTS/raytrace_orig.json" "$RESULTS/raytrace_opt.json" \
    | tee "$RESULTS/raytrace_compare.txt"

echo "== Hardware simulation =="
iverilog -g2012 -o "$RESULTS/sim_ray_sphere" hardware_raytrace/q16_sqrt.sv \
    hardware_raytrace/ray_sphere_intersect.sv hardware_raytrace/tb_ray_sphere.sv
vvp "$RESULTS/sim_ray_sphere" | tee "$RESULTS/simulation.log"
if grep -q FAILED "$RESULTS/simulation.log"; then
    echo "Hardware simulation failed"
    exit 1
fi
