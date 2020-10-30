from nion.swift.model import HardwareSource

from nionswift_plugin.server_mod import server_inst, server_panel


def run():
    simpleInstrument = server_inst.serverDevice()
    HardwareSource.HardwareSourceManager().register_instrument("server_display", simpleInstrument)
    server_panel.run(simpleInstrument)


