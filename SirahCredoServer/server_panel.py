# standard libraries
import gettext
from nion.swift import Panel
from nion.swift import Workspace
from nion.ui import Declarative
from nion.ui import UserInterface
from . import server_inst
import numpy

_ = gettext.gettext

class serverhandler:

    def __init__(self, instrument: server_inst.serverDevice, document_controller):

        self.event_loop = document_controller.event_loop
        self.document_controller = document_controller
        self.instrument = instrument
        self.enabled = False
        #self.property_changed_event_listener = self.instrument.property_changed_event.listen(self.prepare_widget_enable)

    def init_handler(self):
        pass
        #self.event_loop.create_task(self.do_enable(False, ['init_pb']))

    def init(self, widget):
        ok = self.instrument.init()
        if ok:
            self.init_pb.enabled = False
            self.event_loop.create_task(self.do_enable(True, ['init_pb']))
            self.instrument.loop()

    def click(self, widget):
        pass

    async def do_enable(self, enabled=True, not_affected_widget_name_list=None):
        for var in self.__dict__:
            if var not in not_affected_widget_name_list:
                if isinstance(getattr(self, var), UserInterface.Widget):
                    widg = getattr(self, var)
                    setattr(widg, "enabled", enabled)

    def prepare_widget_enable(self, value):
        self.event_loop.create_task(self.do_enable(True, ['']))

    def prepare_widget_disable(self, value):
        self.event_loop.create_task(self.do_enable(False, ['']))


class serverView:

    def __init__(self, instrument: server_inst.serverDevice):
        ui = Declarative.DeclarativeUI()

        self.init_pb = ui.create_push_button(name='init_pb', on_clicked='init', text='Init')

        self.client_laser = ui.create_label(name='client_laser', text='Client Laser: ')
        self.client_laser_rgb = ui.create_image(image='@binding(instrument.color_laser)', on_clicked='click', width=15)
        self.laser = ui.create_row(self.client_laser, self.client_laser_rgb)

        self.client_pm01 = ui.create_label(name='client_pm01', text='Client Power 01: ')
        self.client_pm01_rgb = ui.create_image(image='@binding(instrument.color_pm01)', on_clicked='click', width=15)
        self.pm01 = ui.create_row(self.client_pm01, self.client_pm01_rgb)

        self.client_pm02 = ui.create_label(name='client_pm02',text='Client Power 02: ')
        self.client_pm02_rgb = ui.create_image(image='@binding(instrument.color_pm02)', on_clicked='click', width=15)
        self.pm02 = ui.create_row(self.client_pm02, self.client_pm02_rgb)

        self.client_ps = ui.create_label(name='client_ps', text='Client Power Supply: ')
        self.client_ps_rgb = ui.create_image(image='@binding(instrument.color_ps)', on_clicked='click', width=15)
        self.ps = ui.create_row(self.client_ps, self.client_ps_rgb)

        self.client_ard = ui.create_label(name='client_ard',text='Client Arduino: ')
        self.client_ard_rgb = ui.create_image(image='@binding(instrument.color_ard)', on_clicked='click', width=15)
        self.ard = ui.create_row(self.client_ard,  self.client_ard_rgb)

        self.ui_view = ui.create_column(self.init_pb, self.laser, self.pm01, self.pm02, self.ps, self.ard)

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


def run(instrument: server_inst.serverDevice) -> None:
    panel_id = "Server Status"  # make sure it is unique, otherwise only one of the panel will be displayed
    name = _("Server Staus")
    Workspace.WorkspaceManager().register_panel(create_spectro_panel, panel_id, name, ["left", "right"], "left",
                                                {"instrument": instrument})
