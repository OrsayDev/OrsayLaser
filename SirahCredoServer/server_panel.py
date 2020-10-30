# standard libraries
import gettext
from nion.swift import Panel
from nion.swift import Workspace
from nion.ui import Declarative
from nion.ui import UserInterface
from nionswift_plugin.laser_mod import gain_inst

_ = gettext.gettext

class serverhandler:

    def __init__(self, instrument: gain_inst.gainDevice, document_controller):

        self.event_loop = document_controller.event_loop
        self.document_controller = document_controller
        self.instrument = instrument
        self.enabled = False
        self.busy_event_listener = self.instrument.busy_event.listen(self.prepare_widget_disable)
        self.property_changed_event_listener = self.instrument.property_changed_event.listen(self.prepare_widget_enable)
        self.free_event_listener = self.instrument.free_event.listen(self.prepare_free_widget_enable)


    def init_handler(self):
        self.event_loop.create_task(self.do_enable(True, ['']))
        self.event_loop.create_task(self.do_enable(False, ['init_pb', 'server_ping_push', 'host_value', 'port_value',
                                                           'server_value', 'server_choice']))  # not working as something is calling this guy


    async def do_enable(self, enabled=True, not_affected_widget_name_list=None):
        for var in self.__dict__:
            if var not in not_affected_widget_name_list:
                if isinstance(getattr(self, var), UserInterface.Widget):
                    widg = getattr(self, var)
                    setattr(widg, "enabled", enabled)

    def prepare_widget_enable(self, value):
        self.event_loop.create_task(self.do_enable(False, ['']))

    def prepare_widget_disable(self, value):
        self.event_loop.create_task(self.do_enable(False, ['']))

    def prepare_free_widget_enable(self,
                                   value):  # THAT THE SECOND EVENT NEVER WORKS. WHAT IS THE DIF BETWEEN THE FIRST?
        self.event_loop.create_task(
            self.do_enable(True, ['']))

class serverView:

    def __init__(self, instrument: gain_inst.gainDevice):
        ui = Declarative.DeclarativeUI()

        self.host_label = ui.create_label(text='Host: ')
        self.ui_view = ui.create_column(self.host_label)

def create_spectro_panel(document_controller, panel_id, properties):
    instrument = properties["instrument"]
    ui_handler = serverhandler(instrument, document_controller)
    ui_view = serverView(instrument)
    panel = Panel.Panel(document_controller, panel_id, properties)

    finishes = list()
    panel.widget = Declarative.construct(document_controller.ui, None, ui_view.ui_view, ui_handler, finishes)

    for finish in finishes:
        finish()
    if ui_handler and hasattr(ui_handler, "init_handler"):
        ui_handler.init_handler()
    return panel


def run(instrument: gain_inst.gainDevice) -> None:
    panel_id = "Server Status"  # make sure it is unique, otherwise only one of the panel will be displayed
    name = _("Server Staus")
    Workspace.WorkspaceManager().register_panel(create_spectro_panel, panel_id, name, ["left", "right"], "left",
                                                {"instrument": instrument})
