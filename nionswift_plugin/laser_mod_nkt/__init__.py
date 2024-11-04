from nion.utils import Registry

from . import gain_inst
from . import gain_panel

def run():
    simpleInstrument=gain_inst.gainDevice()
    Registry.register_component(simpleInstrument, {"sgain_controller_nkt"})
    gain_panel.run(simpleInstrument)