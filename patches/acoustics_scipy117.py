"""Patch acoustics.directivity for scipy >=1.17 (sph_harm removed).

Run after installing deps:
    python patches/acoustics_scipy117.py
"""

import os
import acoustics

target = os.path.join(os.path.dirname(acoustics.__file__), "directivity.py")

with open(target) as f:
    src = f.read()

old = "from scipy.special import sph_harm  # pylint: disable=no-name-in-module"
new = """\
try:
    from scipy.special import sph_harm  # pylint: disable=no-name-in-module
except ImportError:
    from scipy.special import sph_harm_y as _sph_harm_y
    def sph_harm(m, n, theta, phi):
        return _sph_harm_y(n, m, phi, theta)"""

if old in src:
    src = src.replace(old, new)
    with open(target, "w") as f:
        f.write(src)
    print(f"Patched {target}")
else:
    print(f"Already patched or import not found in {target}")
