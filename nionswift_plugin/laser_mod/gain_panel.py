# standard libraries
import gettext
import numpy

# local libraries
from nion.swift import Panel
from nion.swift import Workspace
#from nion.swift.Model import DataItem
from nion.ui import Widgets
from nion.utils import Binding
from nion.utils import Converter
from nion.utils import Geometry
from nion.ui import Declarative
from nion.ui import UserInterface
from nion.swift.model import DataItem
import threading

from . import gain_inst
import logging
_ = gettext.gettext
from nion.utils import Model



import inspect


class gainhandler:


    #def __init__(self, instrument:gain_inst.gainDevice, event_loop): #MATHIEU
    def __init__(self, instrument:gain_inst.gainDevice, document_controller):

        #self.event_loop=event_loop #MATHIEU
        self.event_loop=document_controller.event_loop
        self.document_controller=document_controller
        self.instrument=instrument
        self.enabled = False
        self.property_changed_event_listener=self.instrument.property_changed_event.listen(self.prepare_widget_enable)
        self.free_event_listener=self.instrument.free_event.listen(self.prepare_free_widget_enable)
        self.busy_event_listener=self.instrument.busy_event.listen(self.prepare_widget_disable)

    def init_push(self, widget):
        self.instrument.init()
        self.init_pb.enabled=False

    def upt_push(self, widget):
        self.instrument.upt()
    
    def acq_push(self, widget):
        self.instrument.acq()
        #test_data = numpy.random.randn(10, 10)
        #self.live_data_item = DataItem.DataItem(large_format=True)
        #self.live_data_item.set_data(test_data)
        #self.document_controller.document_model.append_data_item(self.live_data_item)

    def gen_push(self, widget):
        data_item, data_item2, data_item3, data_item4 = self.instrument.gen()
        if data_item!=None:
            self.document_controller.document_model.append_data_item(data_item)
            display_item = self.document_controller.document_model.get_display_item_for_data_item(data_item)
            self.document_controller.show_display_item(display_item)
			
            self.document_controller.document_model.append_data_item(data_item2)
            display_item2 = self.document_controller.document_model.get_display_item_for_data_item(data_item2)
            self.document_controller.show_display_item(display_item2)
   
            self.document_controller.document_model.append_data_item(data_item3)
            display_item3 = self.document_controller.document_model.get_display_item_for_data_item(data_item3)
            self.document_controller.show_display_item(display_item3)			
			
            self.document_controller.document_model.append_data_item(data_item4)
            display_item4 = self.document_controller.document_model.get_display_item_for_data_item(data_item4)
            self.document_controller.show_display_item(display_item4)
			
        else:
            logging.info("Nothing to generate. Is Stored is True?")
        

    def abt_push(self, widget):
        self.instrument.abt()

    def sht_push(self, widget):
        self.instrument.sht()

    def dio_check(self, widget, checked):
        self.instrument.diode(checked)

    def q_check(self, widget, checked):
        self.instrument.q(checked)

    def ctrl_check(self, widget, checked):
        self.instrument.ctrl_cur(checked)

    async def do_enable(self,enabled=True,not_affected_widget_name_list=None):
        for var in self.__dict__:
            if var not in not_affected_widget_name_list:
                if isinstance(getattr(self,var),UserInterface.Widget):
                    widg=getattr(self,var)
                    setattr(widg, "enabled", enabled)

    def prepare_widget_enable(self, value):
        self.event_loop.create_task(self.do_enable(False, ["init_pb", "abt_pb"]))

    def prepare_widget_disable(self,value):
        self.event_loop.create_task(self.do_enable(False, ["init_pb"]))
    
    def prepare_free_widget_enable(self,value): #THAT THE SECOND EVENT NEVER WORKS. WHAT IS THE DIF BETWEEN THE FIRST?
        self.event_loop.create_task(self.do_enable(True, ["init_pb"]))
    



class gainView:


    def __init__(self, instrument:gain_inst.gainDevice):
        ui = Declarative.DeclarativeUI()


        self.init_pb=ui.create_push_button(text="Init", name="init_pb", on_clicked="init_push")
        
        self.start_label=ui.create_label(text='Start Wavelength (nm): ')
        self.start_line = ui.create_line_edit(text="@binding(instrument.start_wav_f)", name="start_line")
        self.pts_label=ui.create_label(text='E-points: ')
        self.pts_value_label = ui.create_label(text="@binding(instrument.pts_f)")
        self.ui_view1 = ui.create_row(self.start_label, self.start_line, ui.create_stretch(), self.pts_label, self.pts_value_label, spacing=12)
        
        self.finish_label=ui.create_label(text='Finish Wavelength (nm): ')
        self.finish_line = ui.create_line_edit(text="@binding(instrument.finish_wav_f)", name="finish_line")
        self.tpts_label=ui.create_label(text='Total points: ')
        self.tpts_value_label = ui.create_label(text='@binding(instrument.tpts_f)')
        self.ui_view2 = ui.create_row(self.finish_label, self.finish_line, ui.create_stretch(), self.tpts_label, self.tpts_value_label, spacing=12)

        self.step_label=ui.create_label(text='Step Wavelength (nm): ')
        self.step_line = ui.create_line_edit(text="@binding(instrument.step_wav_f)", name="step_line")
        self.current_label=ui.create_label(text='Current Wavelength (nm): ')
        self.current_value_label = ui.create_label(text='@binding(instrument.cur_wav_f)')
        self.ui_view3 = ui.create_row(self.step_label, self.step_line, ui.create_stretch(), self.current_label, self.current_value_label, spacing=12)
        
        self.avg_label=ui.create_label(text='Averages: ')
        self.avg_line = ui.create_line_edit(text="@binding(instrument.avg_f)", name="avg_line")
        self.running_label=ui.create_label(text='Is running? ')
        self.running_value_label = ui.create_label(text='@binding(instrument.run_status)')
        self.ui_view4 = ui.create_row(self.avg_label, self.avg_line, ui.create_stretch(), self.running_label, self.running_value_label, spacing=12)
        
        self.dwell_label=ui.create_label(text='Dwell Time (ms): ')
        self.dwell_line = ui.create_line_edit(text="@binding(instrument.dwell_f)", name="dwell_line")
        self.stored_label=ui.create_label(text='Stored Data? ')
        self.stored_value_label = ui.create_label(text='@binding(instrument.stored_status)')
        self.ui_view5 = ui.create_row(self.dwell_label, self.dwell_line, ui.create_stretch(), self.stored_label, self.stored_value_label, spacing=12)
        
        self.upt_pb=ui.create_push_button(text="Update", name="upt_pb", on_clicked="upt_push")
        self.acq_pb=ui.create_push_button(text="Acquire", name="acq_pb", on_clicked="acq_push")
        self.gen_pb=ui.create_push_button(text="Generate", name="gen_pb", on_clicked="gen_push")
        self.abt_pb=ui.create_push_button(text="Abort", name="abt_pb", on_clicked="abt_push")
        self.ui_view6 = ui.create_row(self.upt_pb, self.acq_pb, self.gen_pb, self.abt_pb, spacing=12) #yves: Note that i removed update button. It is useless

        self.power_label=ui.create_label(text='Power (uW): ')
        self.power_value_label = ui.create_label(text="@binding(instrument.power_f)")
        self.ui_view7 = ui.create_row(self.power_label, self.power_value_label, ui.create_stretch(), spacing=12)

        self.line_label=ui.create_label(text='-', width=2)
        self.ui_view_line = ui.create_row(ui.create_stretch(), self.line_label, ui.create_stretch())

        self.diode_label = ui.create_label(text='Diodes: ')
        self.diode_checkbox = ui.create_check_box(name="diode_checkbox", on_checked_changed='dio_check')
        self.diode_value_label=ui.create_label(text="@binding(instrument.d_f)")
        self.q_label = ui.create_label(text='Q Switch: ')
        self.q_checkbox = ui.create_check_box(name="q_checkbox", on_checked_changed='q_check')
        self.q_value_label=ui.create_label(text='@binding(instrument.q_f)')
        self.control_label = ui.create_label(text="Control: ")
        self.control_checkbox = ui.create_check_box(name="control_checkbox", on_checked_changed='ctrl_check')
        self.shutter_pb=ui.create_push_button(text='Shutter', name="sht_pb", on_clicked='sht_push')
        self.ui_view8=ui.create_row(self.diode_label, self.diode_checkbox, self.diode_value_label, ui.create_stretch(), self.q_label, self.q_checkbox, self.q_value_label, ui.create_stretch(), self.control_label, self.control_checkbox, ui.create_stretch(), self.shutter_pb, spacing=12)

        self.diode_cur_label=ui.create_label(text='Current 01: ')
        self.diode_cur_value_label=ui.create_label(text="@binding(instrument.cur_d1_f)")
        self.diode_cur2_label=ui.create_label(text='Current 02: ')
        self.diode_cur2_value_label = ui.create_label(text='@binding(instrument.cur_d2_f)')
        self.shutter_label02=ui.create_label(text='Shutter: ')
        self.shutter_label02_value=ui.create_label(text='@binding(instrument.sht_f)')
        self.ui_view9=ui.create_row(self.diode_cur_label, self.diode_cur_value_label, self.diode_cur2_label, self.diode_cur2_value_label, ui.create_stretch(), self.shutter_label02, self.shutter_label02_value, spacing=12)

        self.diode_cur_label=ui.create_label(text='Diode(1, 2) (A): ')
        self.diode_cur_slider=ui.create_slider(name="cur_slider", value='@binding(instrument.cur_d_f)', minimum=10, maximum=2800)
        self.ui_view10=ui.create_row(self.diode_cur_label, self.diode_cur_slider, ui.create_stretch())

        self.ascii_label=ui.create_label(text='@binding(instrument.ascii_f)')
        self.ui_view11 = ui.create_row(ui.create_stretch(), self.ascii_label, ui.create_stretch())


        self.ui_view=ui.create_column(self.init_pb, self.ui_view1, self.ui_view2, self.ui_view3, self.ui_view4, self.ui_view5, self.ui_view6, self.ui_view7, self.ui_view_line, self.ui_view8, self.ui_view9, self.ui_view10, self.ui_view11, spacing=1)



        
def create_spectro_panel(document_controller, panel_id, properties):
        instrument = properties["instrument"]
        #ui_handler =gainhandler(instrument, document_controller.event_loop) #MATHIEU
        ui_handler =gainhandler(instrument, document_controller)
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
    panel_id = "Laser"#make sure it is unique, otherwise only one of the panel will be displayed
    name = _("Laser")
    Workspace.WorkspaceManager().register_panel(create_spectro_panel, panel_id, name, ["left", "right"], "left",
                                                {"instrument": instrument})
