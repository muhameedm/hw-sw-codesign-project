#!/bin/bash
cd ~/perfstat
EV=instructions,cycles,cache-references,cache-misses,branches,branch-misses
for spec in "bm_raytrace 10" "opt_raytrace 10" "bm_pyflate 3" "opt_pyflate 3"; do
  set -- $spec
  taskset -c 40 perf stat -r ${REPS:-5} -x, -e $EV -o stat_$1.csv python3 perf_driver.py $1/run_benchmark.py $2
  echo "$1 done"
done
