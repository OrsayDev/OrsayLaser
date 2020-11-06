# standard libraries
import gettext
from nion.swift import Panel
from nion.swift import Workspace
from nion.ui import Declarative
from nion.ui import UserInterface
from nionswift_plugin.server_mod import server_inst

_ = gettext.gettext

class serverhandler:

    def __init__(self, instrument: server_inst.serverDevice, document_controller):
        self.event_loop = document_controller.event_loop
        self.document_controller = document_controller
        self.instrument = instrument
        self.enabled = False
        self.property_changed_event_listener = self.instrument.property_changed_event.listen(self.prepare_widget_enable)

    def init_handler(self):
        self.event_loop.create_task(self.do_enable(False, ['init_pb']))

    def init(self, widget):
        ok = self.instrument.init()
        if ok:
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
        self.event_loop.create_task(self.do_enable(True, ['init_pb']))



class serverView:

    def __init__(self, instrument: server_inst.serverDevice):
        ui = Declarative.DeclarativeUI()

        self.host_label = ui.create_label(text='Host:')
        self.host_value = ui.create_line_edit(text='@binding(instrument.host)')
        self.host_row = ui.create_row(self.host_label, self.host_value, spacing=12)
        self.port_label = ui.create_label(text='Port:')
        self.port_value = ui.create_line_edit(text='@binding(instrument.port)')
        self.port_row = ui.create_row(self.port_label, self.port_value, spacing=12)

        self.init_pb = ui.create_push_button(name='init_pb', on_clicked='init', text='[Re-]Connect', icon='@binding(instrument.server_status)')

        self.header_rx = ui.create_label(text='Rx')
        self.header_tx = ui.create_label(text='Tx')
        self.header_row = ui.create_row(ui.create_stretch(), self.header_rx, self.header_tx, spacing=12)

        self.client_laser = ui.create_label(name='client_laser', text='Client Laser: ')
        self.client_laser_rx = ui.create_push_button(icon='@binding(instrument.laser_rx)', on_clicked='click',
                                                     width=25)
        self.client_laser_tx = ui.create_push_button(icon='@binding(instrument.laser_tx)', on_clicked='click',
                                                      width=25)
        self.laser = ui.create_row(self.client_laser, self.client_laser_rx, self.client_laser_tx)

        self.client_pm0 = ui.create_label(name='client_pm01', text='Client Power 0: ')
        self.client_pm0_rx = ui.create_push_button(icon='@binding(instrument.pm0_rx)', on_clicked='click',
                                                     width=25)
        self.client_pm0_tx = ui.create_push_button(icon='@binding(instrument.pm0_tx)', on_clicked='click',
                                                   width=25)
        self.pm01 = ui.create_row(self.client_pm0, self.client_pm0_rx, self.client_pm0_tx)

        self.client_pm1 = ui.create_label(name='client_pm02',text='Client Power 1: ')
        self.client_pm1_rx = ui.create_push_button(icon='@binding(instrument.pm1_rx)', on_clicked='click',
                                                     width=25)
        self.client_pm1_tx = ui.create_push_button(icon='@binding(instrument.pm1_tx)', on_clicked='click',
                                                   width=25)
        self.pm02 = ui.create_row(self.client_pm1, self.client_pm1_rx, self.client_pm1_tx)

        self.client_ps = ui.create_label(name='client_ps', text='Client Power Supply: ')
        self.client_ps_rx = ui.create_push_button(icon='@binding(instrument.ps_rx)', on_clicked='click',
                                                   width=25)
        self.client_ps_tx = ui.create_push_button(icon='@binding(instrument.ps_tx)', on_clicked='click',
                                                  width=25)
        self.ps = ui.create_row(self.client_ps, self.client_ps_rx, self.client_ps_tx)

        self.client_ard = ui.create_label(name='client_ard',text='Client Arduino: ')
        self.client_ard_rx = ui.create_push_button(icon='@binding(instrument.ard_rx)', on_clicked='click',
                                                    width=25)
        self.client_ard_tx = ui.create_push_button(icon='@binding(instrument.ard_tx)', on_clicked='click',
                                                   width=25)
        self.ard = ui.create_row(self.client_ard,  self.client_ard_rx, self.client_ard_tx)


        self.ui_view = ui.create_column(self.host_row, self.port_row, self.init_pb, self.header_row, self.laser, self.pm01, self.pm02, self.ps, self.ard)

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
    name = _("Server Status")
    Workspace.WorkspaceManager().register_panel(create_spectro_panel, panel_id, name, ["left", "right"], "left",
                                                {"instrument": instrument})
