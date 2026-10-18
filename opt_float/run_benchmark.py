"""
Artificial, floating point-heavy benchmark originally used by Factor.
"""
import pyperf

from math import sin, cos, sqrt


POINTS = 100000


class Point(object):
    __slots__ = ('x', 'y', 'z')

    def __init__(self, i):
        self.x = x = sin(i)
        self.y = cos(i) * 3
        self.z = (x * x) / 2

    def __repr__(self):
        return "<Point: x=%s, y=%s, z=%s>" % (self.x, self.y, self.z)

    def normalize(self):
        x = self.x
        y = self.y
        z = self.z
        norm = sqrt(x * x + y * y + z * z)
        self.x /= norm
        self.y /= norm
        self.z /= norm

    def maximize(self, other):
        self.x = self.x if self.x > other.x else other.x
        self.y = self.y if self.y > other.y else other.y
        self.z = self.z if self.z > other.z else other.z
        return self


def maximize(points):
    p0 = points[0]
    mx, my, mz = p0.x, p0.y, p0.z
    for p in points[1:]:
        px, py, pz = p.x, p.y, p.z
        if px > mx: mx = px
        if py > my: my = py
        if pz > mz: mz = pz
    p0.x, p0.y, p0.z = mx, my, mz
    return p0


def benchmark(n):
    points = [None] * n
    for i in range(n):
        points[i] = Point(i)
    for p in points:
        p.normalize()
    return maximize(points)


if __name__ == "__main__":
    runner = pyperf.Runner()
    runner.metadata['description'] = "Float benchmark"

    points = POINTS
    runner.bench_func('float', benchmark, points)
