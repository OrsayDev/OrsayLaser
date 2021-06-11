import setuptools

setuptools.setup(
    name="OrsayLaser",
    version="5.13.5",
    author="Yves Auad",
    description="Laser Control",
    url="https://github.com/yvesauad/yvorsay-instrument",
    packages=["nionswift_plugin.laser_mod", "SirahCredoServer", "SirahCredoServer.virtualInstruments"],
    python_requires='~=3.6',
    install_requires=["pyserial>=3.4", "pyusb>=1.0.2", "PyVISA>=1.10.1", "PyVISA-py>=0.4.1", "nionswift-usim>=0.3.0"]
)