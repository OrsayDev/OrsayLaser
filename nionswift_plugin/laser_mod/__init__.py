from nion.swift.model import HardwareSource


import logging
from . import gain_inst
from . import gain_panel
from SirahCredoServer import server_panel


def run():

    simpleInstrument=gain_inst.gainDevice()
    HardwareSource.HardwareSourceManager().register_instrument("sgain_controller", simpleInstrument)
    gain_panel.run(simpleInstrument)
    server_panel.run(simpleInstrument)


