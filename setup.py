from setuptools import setup


setup(
    name="OrsayLaser",
    version="6.5.2",
    author="Yves Auad",
    description="Laser Control",
    url="https://github.com/yvesauad/yvorsay-instrument",
    packages=['nionswift_plugin.laser_mod', 'SirahCredoServer', 'SirahCredoServer.virtualInstruments'],
    packages_dir = {'nionswift_plugin.laser_mod': 'src/nionswft_plugin/laser_mod'},
    package_data = {'nionswift_plugin.laser_mod': ['aux_files/dif_delays/*', 'aux_files/*']},
    python_requires='>=3.8.5',
    install_requires=["pyserial>=3.4", "pyusb>=1.0.2", "PyVISA>=1.10.1", "PyVISA-py>=0.4.1"]
)