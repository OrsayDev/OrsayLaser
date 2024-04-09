from nion.utils import Registry

from nionswift_plugin.server_mod import server_inst, server_panel

def run():
    simpleInstrument = server_inst.serverDevice()
    Registry.register_component(simpleInstrument, {"server_display"})
    server_panel.run(simpleInstrument)


