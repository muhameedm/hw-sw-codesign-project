"""Runs a benchmark a fixed number of loops in one process, for perf stat."""
import importlib.util, os, sys, time, types
sys.modules["pyperf"] = types.SimpleNamespace(perf_counter=time.perf_counter, Runner=None)
path, loops = sys.argv[1], int(sys.argv[2])
spec = importlib.util.spec_from_file_location("bench", path)
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
if "raytrace" in path:
    m.bench_raytrace(loops, m.DEFAULT_WIDTH, m.DEFAULT_HEIGHT, None)
else:
    m.bench_pyflake(loops, os.path.join(os.path.dirname(path), "data", "interpreter.tar.bz2"))
