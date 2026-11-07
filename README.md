# HW/SW Co-design Final Project (00460882)

Profiling, optimizing and proposing hardware acceleration for two pyperformance
benchmarks: `raytrace` and `pyflate`.

## Results

| Benchmark | Original | Optimized | Speedup |
|---|---|---|---|
| raytrace | 17.5 s +- 2.8 s | 11.6 s +- 2.3 s | 1.52x |
| pyflate | 18.5 s +- 1.6 s | 5.56 s +- 1.20 s | 3.32x |

Measured with `pyperf compare_to` in the course QEMU VM. The emulated VM is noisy,
so see the reports for how to read these numbers. Hardware counters are not
available in the VM, so `perf_stat/` holds counters measured directly on the host.

## Repository structure

| Path | Contents |
|---|---|
| `bm_raytrace/`, `bm_pyflate/` | Original benchmarks |
| `opt_raytrace/`, `opt_pyflate/` | Optimized benchmarks |
| `hardware_raytrace/` | Ray-sphere accelerator in SystemVerilog and its testbench |
| `report_raytrace.txt`, `report_pyflate.txt` | Analysis, results and hardware proposal |
| `script_raytrace.sh`, `script_pyflate.sh` | Reproduce the full flow |
| `*_orig.svg`, `*_opt.svg` | Flame graphs before and after optimization |
| `*_orig.json`, `*_opt.json`, `*_compare.txt` | pyperf measurements |
| `initial_raytrace_report.txt`, `pyflate_*_perf_report.txt` | `perf report` output |
| `perf_stat/` | Hardware counters measured on the host, and the driver that collects them |
| `presentation/` | Slides and the script that builds them |
| `prompt.txt` | AI tool usage |

## Requirements

- The course QEMU VM (Ubuntu 22.04, Python 3.10)
- `perf` and `pyperf`
- [FlameGraph](https://github.com/brendangregg/FlameGraph), expected in
  `/root/FlameGraph` or set through `FLAMEGRAPH_DIR`
- Icarus Verilog, for the hardware simulation

The scripts install missing tools when the machine has internet access.

## How to run

From the repository root, inside the VM:

```bash
./script_raytrace.sh
./script_pyflate.sh
```

Each script writes profiles, flame graphs, measurements and comparisons to
`results/`. On the VM, a full run takes a long time because pyperf spawns many
worker processes.

To run only the hardware simulation:

```bash
cd hardware_raytrace
iverilog -g2012 -o sim_ray_sphere q16_sqrt.sv ray_sphere_intersect.sv tb_ray_sphere.sv
vvp sim_ray_sphere
```

Expected output:

```
TEST 1 PASSED: Direct Hit at t = 8.000000
TEST 2 PASSED: Correctly detected Miss
ALL HARDWARE TESTS COMPLETED.
```
