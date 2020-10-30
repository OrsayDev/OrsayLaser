from nion.swift.model import HardwareSource

from nionswift_plugin.server_mod import server_inst, server_panel


def run():
    simpleServer = server_inst.serverDevice()
    HardwareSource.HardwareSourceManager().register_instrument("server_display", simpleServer)
    server_panel.run(simpleServer)


