from setuptools import setup

setup(
    name="OrsayLaser",
    version="5.16.1",
    author="Yves Auad",
    description="Laser Control",
    url="https://github.com/yvesauad/yvorsay-instrument",
    packages=['nionswift_plugin.laser_mod', 'SirahCredoServer', 'SirahCredoServer.virtualInstruments'],
    data_files=[('nionswift_plugin/laser_mod/aux_files', [
                 'nionswift_plugin/laser_mod/aux_files/Pyrromethene_597.npy',
                 'nionswift_plugin/laser_mod/aux_files/Pyrromethene_597.json',
        ]), ('nionswift_plugin/laser_mod/aux_files/dif_delays', [
        'nionswift_plugin/laser_mod/aux_files/dif_delays/50.txt'
    ]
             )],
    python_requires='>=3.8.5',
    install_requires=["pyserial>=3.4", "pyusb>=1.0.2", "PyVISA>=1.10.1", "PyVISA-py>=0.4.1"]
)