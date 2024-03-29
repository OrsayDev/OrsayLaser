from nion.instrumentation import HardwareSource

from . import gain_inst
from . import gain_panel

def run():
    simpleInstrument=gain_inst.gainDevice()
    HardwareSource.HardwareSourceManager().register_instrument("sgain_controller", simpleInstrument)
    gain_panel.run(simpleInstrument)