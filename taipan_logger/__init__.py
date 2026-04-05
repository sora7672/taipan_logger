"""
Public interface of the taipan logger package.
Exposes the logger singleton, the configure function, and the trace decorator
for use by any code that imports this package.

:author: sora7672
"""

__author__: str = "sora7672"
__version__: str = "1.0.0"
__date__: str = "2026-04-05"
__description__: str = "A lightweight, DSGVO-safe, threadsafe, async-ready Python logger."

from .logger import taipan, configure
from .decorator import trace


if __name__ == "__main__":
    print("Dont start the package files alone! The imports wont work like this!")