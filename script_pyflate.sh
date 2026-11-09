#!/bin/bash
# Full pyflate flow: setup, profiling, flame graphs, comparison.
# Run inside the course QEMU VM from the repository root.
set -euo pipefail
cd "$(dirname "$0")"

FLAMEGRAPH_DIR="${FLAMEGRAPH_DIR:-/root/FlameGraph}"
RESULTS=results/pyflate
mkdir -p "$RESULTS"

echo "== Environment setup =="
python3 -c 'import pyperf' 2>/dev/null || python3 -m pip install pyperf
command -v perf >/dev/null || { echo "perf is required"; exit 1; }
[ -d "$FLAMEGRAPH_DIR" ] || git clone https://github.com/brendangregg/FlameGraph "$FLAMEGRAPH_DIR"

flamegraph() {  # name, benchmark path
    perf record -F 999 -g -o "$RESULTS/$1.perf" -- python3-dbg "$2" --values 1 -w 0
    perf report --stdio -i "$RESULTS/$1.perf" > "$RESULTS/$1_perf_report.txt"
    perf script -i "$RESULTS/$1.perf" \
        | "$FLAMEGRAPH_DIR/stackcollapse-perf.pl" \
        | "$FLAMEGRAPH_DIR/flamegraph.pl" > "$RESULTS/$1.svg"
}

echo "== Profiling and flame graphs =="
flamegraph pyflate_orig bm_pyflate/run_benchmark.py
flamegraph pyflate_opt opt_pyflate/run_benchmark.py

echo "== Baseline vs optimized =="
python3 bm_pyflate/run_benchmark.py --values 3 -w 1 -o "$RESULTS/pyflate_orig.json"
python3 opt_pyflate/run_benchmark.py --values 3 -w 1 -o "$RESULTS/pyflate_opt.json"
python3 -m pyperf compare_to "$RESULTS/pyflate_orig.json" "$RESULTS/pyflate_opt.json" \
    | tee "$RESULTS/pyflate_compare.txt"
