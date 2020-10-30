from nion.swift.model import HardwareSource


import logging
from . import gain_inst
from . import gain_panel
from SirahCredoServer import server_panel
from SirahCredoServer import server_inst


def run():

    simpleInstrument=gain_inst.gainDevice()
    simpleServer = server_inst.serverDevice()
    HardwareSource.HardwareSourceManager().register_instrument("sgain_controller", simpleInstrument)
    gain_panel.run(simpleInstrument)
    server_panel.run(simpleServer)


