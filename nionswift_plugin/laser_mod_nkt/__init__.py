from nion.utils import Registry
import logging

is_ok = False
try:
    from . import gain_inst
    from . import gain_panel
    is_ok = True
except FileNotFoundError:
    logging.info("***LASER NKT***: Probably not found DLL. Laser cannot be initialized.")

def run():
    if is_ok:
        simpleInstrument=gain_inst.gainDevice()
        Registry.register_component(simpleInstrument, {"sgain_controller_nkt"})
        gain_panel.run(simpleInstrument)