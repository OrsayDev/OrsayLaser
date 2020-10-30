from nion.swift.model import HardwareSource

from . import server_panel
from . import server_inst

def run():
    simpleServer = server_inst.serverDevice()
    HardwareSource.HardwareSourceManager().register_instrument("server_display", simpleServer)
    server_panel.run(simpleServer)


