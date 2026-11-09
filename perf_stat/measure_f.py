"""Measures the share of raytrace runtime spent in Sphere.intersectionTime.

Records the real calls of one render, then replays exactly those calls without
any instrumentation. Usage: measure_f.py <benchmark file>
"""
import importlib.util, sys, time, types

sys.modules["pyperf"] = types.SimpleNamespace(perf_counter=time.perf_counter, Runner=None)
spec = importlib.util.spec_from_file_location("bench", sys.argv[1])
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)

def render():
    start = time.perf_counter()
    m.bench_raytrace(1, m.DEFAULT_WIDTH, m.DEFAULT_HEIGHT, None)
    return time.perf_counter() - start

original = m.Sphere.intersectionTime
total = min(render() for _ in range(7))

calls = []
def record(self, ray):
    calls.append((self, ray))
    return original(self, ray)
m.Sphere.intersectionTime = record
render()
m.Sphere.intersectionTime = original

def replay():
    start = time.perf_counter()
    for sphere, ray in calls:
        original(sphere, ray)
    return time.perf_counter() - start

def empty():
    start = time.perf_counter()
    for sphere, ray in calls:
        pass
    return time.perf_counter() - start

work = min(replay() for _ in range(7)) - min(empty() for _ in range(7))
print(f"total={total:.4f}s calls={len(calls)} intersect={work:.4f}s "
      f"per_call={1e6 * work / len(calls):.3f}us f={work / total:.4f}")
