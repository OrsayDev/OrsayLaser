import setuptools

setuptools.setup(
    name="yvorsay-instrumentation_laser",
    version="4.11.0",
    author="Yves Auad",
    description="Laser Control",
    url="https://github.com/yvesauad/yvorsay-instrument",
    packages=["nionswift_plugin.laser_mod", "nionswift_plugin.server_mod"],
    python_requires='~=3.6',
    install_requires=["pyserial>=3.4", "pyusb>=1.0.2", "PyVISA>=1.10.1", "PyVISA-py>=0.4.1"]
)