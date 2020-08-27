

import setuptools

setuptools.setup(
    name="yvorsay-instrumentation_laser",
    version="1.7.0.1",
    author="Yves Auad",
    description="Laser Control",
    url="https://github.com/yvesauad/yvorsay-instrument",
    packages=["nionswift_plugin.laser_mod"],
    python_requires='~=3.6',
    install_requires=["pyserial>=3.4", "pyusb>=1.0.2", "PyVISA>=1.10.1", "PyVISA-py>=0.4.1"]
)
