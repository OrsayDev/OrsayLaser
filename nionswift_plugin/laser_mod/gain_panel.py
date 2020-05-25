# standard libraries
import gettext

# local libraries
from nion.swift import Panel
from nion.swift import Workspace
from nion.ui import Widgets
from nion.utils import Binding
from nion.utils import Converter
from nion.utils import Geometry
from nion.ui import Declarative
from nion.ui import UserInterface
import threading

from . import gain_inst
import logging
_ = gettext.gettext
from nion.utils import Model



import inspect


class gainhandler:


    def __init__(self,instrument:gain_inst.gainDevice,event_loop):

        self.event_loop=event_loop
        self.instrument=instrument
        self.enabled = False
        self.property_changed_event_listener=self.instrument.property_changed_event.listen(self.prepare_widget_enable)
        self.busy_event_listener=self.instrument.busy_event.listen(self.prepare_widget_disable)


    def init_push(self, widget):
        self.instrument.init()
        self.init_pb.enabled=False

    def upt_push(self, widget):
        self.instrument.upt()
    
    def acq_push(self, widget):
        self.instrument.acq()

    def gen_push(self, widget):
        self.instrument.gen()

    async def do_enable(self,enabled=True,not_affected_widget_name_list=None):
        #Pythonic way of finding the widgets
        #actually a more straigthforward way would be to create a list of widget in the init_handler
        #then use this list in the present function...
        for var in self.__dict__:
            if var not in not_affected_widget_name_list:
                if isinstance(getattr(self,var),UserInterface.Widget):
                    widg=getattr(self,var)
                    setattr(widg, "enabled", enabled)

    def prepare_widget_enable(self,value):
        # this message will come from a thread. use event loop to call functions on the main thread.
        self.event_loop.create_task(self.do_enable(True,["init_pb"]))
    def prepare_widget_disable(self,value):
        # this message will come from a thread. use event loop to call functions on the main thread.
        self.event_loop.create_task(self.do_enable(False,["init_pb"]))



class gainView:


    def __init__(self, instrument:gain_inst.gainDevice):
        ui = Declarative.DeclarativeUI()


        self.init_pb=ui.create_push_button(text="Init", name="init_pb", on_clicked="init_push")

        
        self.start_label=ui.create_label(text='Start Wavelength (nm): ')
        self.start_line = ui.create_line_edit(text="@binding(instrument.start_wav_f)")
        self.pts_label=ui.create_label(text='E-points: ')
        self.pts_value_label = ui.create_label(text="@binding(instrument.pts_f)")
        self.ui_view1 = ui.create_row(self.start_label, self.start_line, ui.create_stretch(), self.pts_label, self.pts_value_label)
        
        self.finish_label=ui.create_label(text='Finish Wavelength (nm): ')
        self.finish_line = ui.create_line_edit(text="@binding(instrument.finish_wav_f)")
        self.tpts_label=ui.create_label(text='Total points: ')
        self.tpts_value_label = ui.create_label(text='Tpts value')
        self.ui_view2 = ui.create_row(self.finish_label, self.finish_line, ui.create_stretch(), self.tpts_label, self.tpts_value_label)

        self.step_label=ui.create_label(text='Step Wavelength (nm): ')
        self.step_line = ui.create_line_edit(text="@binding(instrument.step_wav_f)")
        self.current_label=ui.create_label(text='Current Wavelength (nm): ')
        self.current_value_label = ui.create_label(text='current value')
        self.ui_view3 = ui.create_row(self.step_label, self.step_line, ui.create_stretch(), self.current_label, self.current_value_label)
        
        self.upt_pb=ui.create_push_button(text="Update", name="upt_pb", on_clicked="upt_push")
        self.acq_pb=ui.create_push_button(text="Acquire", name="acq_pb", on_clicked="acq_push")
        self.gen_pb=ui.create_push_button(text="Generate", name="gen_pb", on_clicked="gen_push")
        self.ui_view4 = ui.create_row(self.upt_pb, self.acq_pb, self.gen_pb)

        self.ui_view=ui.create_column(self.init_pb, self.ui_view1, self.ui_view2, self.ui_view3, self.ui_view4)


        #self.ui_view = ui.create_row(self.init_pb, ui.create_stretch(), self.label, self.start_line)
        #self.button=ui.create_push_button(text="ok")

        #self.ui_view = ui.create_column(self.ui_view, self.button)

   


        
def create_spectro_panel(document_controller, panel_id, properties):
        instrument = properties["instrument"]
        ui_handler =gainhandler(instrument, document_controller.event_loop)
        ui_view=gainView(instrument)
        panel = Panel.Panel(document_controller, panel_id, properties)

        finishes = list()
        panel.widget = Declarative.construct(document_controller.ui, None, ui_view.ui_view, ui_handler, finishes)


        for finish in finishes:
            finish()
        if ui_handler and hasattr(ui_handler, "init_handler"):
            ui_handler.init_handler()
        return panel


def run(instrument: gain_inst.gainDevice) -> None:
    panel_id = "LaserScratch"#make sure it is unique, otherwise only one of the panel will be displayed
    name = _("LaserScratch")
    Workspace.WorkspaceManager().register_panel(create_spectro_panel, panel_id, name, ["left", "right"], "left",
                                                {"instrument": instrument})
