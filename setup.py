# -*- coding: utf-8 -*-

"""
To upload to PyPI, PyPI test, or a local server:
python setup.py bdist_wheel upload -r <server_identifier>
"""

import setuptools
import os

setuptools.setup(
    name="yvorsay-instrumentation",
    version="2.1.0",
    author="Yves Auad, Mathieu Kociak, Marcel Tence",
    description="Gain Control",
    url="https://github.com/yvesauad/yvorsay-instrument",
    packages=["nionswift_plugin.gain_mod"],
    python_requires='~=3.6',
)
