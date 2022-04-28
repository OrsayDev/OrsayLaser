# standard libraries
import gettext
from nion.swift import Panel
from nion.swift import Workspace

from nion.ui import Declarative
from nion.ui import UserInterface
from nion.data import Calibration
from nion.data import DataAndMetadata
from nion.swift.model import DataItem
from nion.swift.model import Utility

from . import gain_inst

import logging
import numpy

_ = gettext.gettext

class DataItemCreation():
    def __init__(self, name, array, signal_dim, offset: list, scale: list, units: list, **kwargs):
        self.metadata = kwargs
        self.timezone = Utility.get_local_timezone()
        self.timezone_offset = Utility.TimezoneMinutesToStringConverter().convert(Utility.local_utcoffset_minutes())

        self.calibration = Calibration.Calibration()
        self.dimensional_calibrations = [Calibration.Calibration() for _ in range(signal_dim)]
        assert len(offset)==len(scale) and len(offset)==len(units)

        for index, x in enumerate(zip(offset, scale, units)):
            self.dimensional_calibrations[index].offset, self.dimensional_calibrations[index].scale, self.dimensional_calibrations[index].units = x[0], x[1], x[2]

        self.xdata = DataAndMetadata.new_data_and_metadata(array, self.calibration, self.dimensional_calibrations,
                                                           metadata=self.metadata,
                                                           timezone=self.timezone, timezone_offset=self.timezone_offset)

        self.data_item = DataItem.DataItem()
        self.data_item.set_xdata(self.xdata)
        self.data_item.title = name
        self.data_item.description = kwargs
        self.data_item.caption = kwargs

    def fast_update_data_only(self, array: numpy.array):
        self.data_item.set_data(array)

    def update_data_only(self, array: numpy.array):
        self.xdata = DataAndMetadata.new_data_and_metadata(array, self.calibration, self.dimensional_calibrations,
                                                           metadata=self.metadata,
                                                           timezone=self.timezone, timezone_offset=self.timezone_offset)
        self.data_item.set_xdata(self.xdata)

class DataItemLaserCreation():
    def __init__(self, title, array, which, start=None, final=None, pts=None, avg=None, step=None, delay=None,
                 time_width=None, start_ps_cur=None, ctrl=None, trans=None, is_live=True, cam_dispersion=1.0, cam_offset=0,
                 power_min=0, power_inc=1, **kwargs):
        self.acq_parameters = {
            "title": title,
            "which": which,
            "start_wav": start,
            "final_wav": final,
            "pts": pts,
            "averages": avg,
            "step_wav": step,
            "delay": delay,
            "time_width": time_width,
            "start_ps_cur": start_ps_cur,
            "control": ctrl,
            "initial_trans": trans
        }
        self.timezone = Utility.get_local_timezone()
        self.timezone_offset = Utility.TimezoneMinutesToStringConverter().convert(Utility.local_utcoffset_minutes())

        self.calibration = Calibration.Calibration()
        self.dimensional_calibrations = [Calibration.Calibration()]

        if which == 'WAV':
            self.calibration.units = 'nm'
        if which == 'POW':
            self.calibration.units = 'μW'
        if which == 'SER':
            self.calibration.units = '°'
        if which == 'PS':
            self.calibration.units = 'A'
        if which == 'transmission_as_wav':
            self.calibration.units = 'T'
            self.dimensional_calibrations[0].units = 'nm'
            self.dimensional_calibrations[0].offset = start
            self.dimensional_calibrations[0].scale = step
        if which == 'power_as_wav':
            self.calibration.units = 'μW'
            self.dimensional_calibrations[0].units = 'nm'
            self.dimensional_calibrations[0].offset = start
            self.dimensional_calibrations[0].scale = step
        if which == 'sEEGS/sEELS_power':
            self.calibration.units = 'A.U.'
            self.dimensional_calibrations[0].units = 'μW'
            self.dimensional_calibrations[0].offset = power_min
            self.dimensional_calibrations[0].scale = power_inc
        if which == 'sEEGS/sEELS':
            self.calibration.units = 'A.U.'
            self.dimensional_calibrations[0].units = 'nm'
            self.dimensional_calibrations[0].offset = start
            self.dimensional_calibrations[0].scale = step
        if which == "CAM_DATA":
            self.dimensional_calibrations = [Calibration.Calibration(), Calibration.Calibration()]
            self.dimensional_calibrations[0].units = 'nm'
            self.dimensional_calibrations[0].offset = start
            self.dimensional_calibrations[0].scale = (step) / avg
            self.dimensional_calibrations[1].units = 'eV'
        if which == "POWER_CAM_DATA":
            self.dimensional_calibrations = [Calibration.Calibration(), Calibration.Calibration()]
            self.dimensional_calibrations[0].units = 'μW'
            self.dimensional_calibrations[0].offset = 0
            self.dimensional_calibrations[0].scale = 1
            self.dimensional_calibrations[1].units = 'eV'
        if which == 'ALIGNED_CAM_DATA':
            self.dimensional_calibrations = [Calibration.Calibration(), Calibration.Calibration()]
            self.dimensional_calibrations[0].units = 'nm'
            self.dimensional_calibrations[0].offset = start
            self.dimensional_calibrations[0].scale = step
            self.dimensional_calibrations[1].units = 'eV'
            self.dimensional_calibrations[1].scale = cam_dispersion
            self.dimensional_calibrations[1].offset = cam_offset

        self.xdata = DataAndMetadata.new_data_and_metadata(array, self.calibration, self.dimensional_calibrations,
                                                           metadata=self.acq_parameters,
                                                           timezone=self.timezone, timezone_offset=self.timezone_offset)

        self.data_item = DataItem.DataItem()
        self.data_item.set_xdata(self.xdata)
        #self.data_item.define_property("title", title)
        self.data_item.title = title
        self.data_item.description = self.acq_parameters
        self.data_item.caption = self.acq_parameters

        if is_live: self.data_item._enter_live_state()

    def update_data_only(self, array: numpy.array):
        self.xdata = DataAndMetadata.new_data_and_metadata(array, self.calibration, self.dimensional_calibrations,
                                                           metadata = self.acq_parameters,
                                                           timezone=self.timezone, timezone_offset=self.timezone_offset)
        self.data_item.set_xdata(self.xdata)

    def fast_update_data_only(self, array: numpy.array):
        self.data_item.set_data(array)

    def set_cam_di_calibration(self, calib: Calibration.Calibration()):
        self.dimensional_calibrations[1] = calib

    def set_cam_di_calibratrion_from_di(self, di: DataItem):
        pass

    def set_dim_calibration(self):
        self.data_item.dimensional_calibrations = self.dimensional_calibrations


class gainhandler:

    def __init__(self, instrument: gain_inst.gainDevice, document_controller):

        self.event_loop = document_controller.event_loop
        self.document_controller = document_controller
        self.instrument = instrument
        self.enabled = False
        self.busy_event_listener = self.instrument.busy_event.listen(self.prepare_widget_disable)
        self.property_changed_event_listener = self.instrument.property_changed_event.listen(self.prepare_widget_enable)
        self.free_event_listener = self.instrument.free_event.listen(self.prepare_free_widget_enable)

        self.call_monitor_listener = self.instrument.call_monitor.listen(self.call_monitor)
        self.call_data_listener = self.instrument.call_data.listen(self.call_data)
        self.append_monitor_data_listener = self.instrument.append_monitor_data.listen(self.append_monitor_data)
        self.append_data_listener = self.instrument.append_data.listen(self.append_data)
        self.end_data_monitor = self.instrument.end_data_monitor.listen(self.end_data_monitor)
        self.end_data_listener = self.instrument.end_data.listen(self.end_data)

        self.server_shutdown_listener = self.instrument.server_shutdown.listen(self.server_shut)

        self.det_acq_listener = self.instrument.det_acq.listen(self.show_det)

        self.__current_DI = None
        self.__current_DI_POW = None
        self.__current_DI_WAV = None

        self.wav_di = None
        self.pow_di = None
        self.pow02_di = None
        self.ser_di = None
        self.ps_di = None
        self.trans_di = None
        self.cam_di = None
        self.aligned_cam_di = None

    def init_handler(self):
        self.event_loop.create_task(self.do_enable(True, ['']))
        self.event_loop.create_task(self.do_enable(False, ['init_pb', 'server_ping_push', 'host_value', 'port_value',
                                                           'server_value', 'server_choice', 'more_m1_pb', 'more_m2_pb',
                                                           'less_m1_pb', 'less_m2_pb']))  # not working as something is calling this guy

    def server_shut(self):
        self.init_pb.enabled = True
        self.server_value.text = 'OFF'
        self.init_handler() #this puts the GUI in the same position as the beginning

    def init_push(self, widget):
        ok = self.instrument.init()
        if ok:
            self.init_pb.enabled = False
            if self.host_value.text == '127.0.0.1':
                self.server_value.text = 'LH'
            elif self.host_value.text == '129.175.82.159':
                self.server_value.text = 'VGLum'
            elif self.host_value.text == '192.168.1.65':
                self.server_value.text = 'Raspberry π'
            else:
                self.server_value.text = 'User-Defined'
            self.event_loop.create_task(
                self.do_enable(True, ['init_pb']))  # not working as something is
        # calling this guy


    def server_choice_pick(self, widget, current_index):
        if current_index == 0:
            self.host_value.text = '127.0.0.1'
            self.port_value.text = '65432'
        if current_index == 1:
            self.host_value.text = '129.175.82.159'
            self.port_value.text = '65432'
        if current_index == 2:
            self.host_value.text = '192.168.1.65'
            self.port_value.text = '65432'

        self.instrument.host_f = self.host_value.text
        self.instrument.port_f = int(self.port_value.text)

    def server_ping_push(self, widget):
        self.instrument.server_instrument_ping()

    def server_shutdown_push(self, widget):
        self.instrument.server_instrument_shutdown()
        self.server_shut()

    def upt_push(self, widget):
        self.instrument.upt()

    def acq_push(self, widget):
        self.instrument.acq()

    def mon_push(self, widget):
        self.instrument.acq_mon()

    def acq_trans_push(self, widget):
        logging.info("***PANEL***: Transmission is disabled. This probably"
                     " happened because we have a broken function.")
        #self.instrument.acq_trans()

    def acq_pr_push(self, widget):
        self.instrument.acq_pr()

    def abt_push(self, widget):
        self.instrument.abt()

    def sht_push(self, widget):
        self.instrument.sht()

    def lock_push(self, widget):
        self.instrument.lock()

    def pw_hard_reset(self, widget):
        self.instrument.hard_reset()

    def more_push(self, widget):
        self.instrument.cur_d_f += 5

    def less_push(self, widget):
        self.instrument.cur_d_f -= 5

    def more_piezo_push(self, widget):
        if widget == self.more_m1_pb:
            self.instrument.piezo_m1_f += self.instrument.piezo_step_f
        elif widget == self.more_m2_pb:
            self.instrument.piezo_m2_f += self.instrument.piezo_step_f

    def less_piezo_push(self, widget):
        if widget == self.less_m1_pb:
            self.instrument.piezo_m1_f -= self.instrument.piezo_step_f
        elif widget == self.less_m2_pb:
            self.instrument.piezo_m2_f -= self.instrument.piezo_step_f

    def more_servo_push(self, widget):
        self.instrument.servo_f += self.instrument.servo_step_f
        self.instrument.property_changed_event.fire('servo_f')
        self.instrument.free_event.fire("all")

    def less_servo_push(self, widget):
        self.instrument.servo_f -= self.instrument.servo_step_f
        self.instrument.property_changed_event.fire('servo_f')
        self.instrument.free_event.fire("all")

    def change_periodic_pic(self, widget, check_state):
        self.periodic_pics_value.enabled = (check_state == 'checked')
        self.periodic_pics_label.enabled = (check_state == 'checked')

    async def data_item_show(self, DI):
        self.document_controller.document_model.append_data_item(DI)

    async def data_item_remove(self, DI):
        self.document_controller.document_model.remove_data_item(DI)

    async def data_item_exit_live(self, DI):
        DI._exit_live_state()

    async def do_enable(self, enabled=True, not_affected_widget_name_list=None):
        for var in self.__dict__:
            if var not in not_affected_widget_name_list:
                if isinstance(getattr(self, var), UserInterface.Widget):
                    widg = getattr(self, var)
                    setattr(widg, "enabled", enabled)

    def prepare_widget_enable(self, value):
        self.event_loop.create_task(self.do_enable(False, ["init_pb", 'host_value', 'port_value', 'abt_pb']))

    def prepare_widget_disable(self, value):
        self.event_loop.create_task(self.do_enable(False, ["init_pb", 'host_value', 'port_value', 'abt_pb']))

    def prepare_free_widget_enable(self,
                                   value):  # THAT THE SECOND EVENT NEVER WORKS. WHAT IS THE DIF BETWEEN THE FIRST?
        self.event_loop.create_task(
            self.do_enable(True, ['init_pb', 'host_value', 'port_value', 'plot_power_wav', 'align_zlp_max', 'align_zlp_fit', 'smooth_zlp',
                                  'process_eegs_pb',
                                  'process_power_pb', 'fit_pb',
                                  'cancel_pb'
                                  ]))

    def show_det(self, xdatas, mode, nacq, npic, show):

        for data_items in self.document_controller.document_model._DocumentModel__data_items:
            if data_items.title == 'Laser Wavelength ' + str(nacq):
                nacq += 1

        #while self.document_controller.document_model.get_data_item_by_title(
        #        'Laser Wavelength ' + str(nacq)) is not None:
        #    nacq += 1  # this puts always a new set even if swift crashes and counts perfectly

        for i, xdata in enumerate(xdatas):
            data_item = DataItem.DataItem()
            data_item.set_xdata(xdata)
            # this nacq-1 is bad. Because Laser Wavelength DI would already be created, this is the easy solution.
            # so, in order for this to work you need to create laser wavelength before creating my haadf/bf DI
            if mode == 'init' or mode == 'end': data_item.define_property("title",
                                                                          mode + '_det' + str(i) + ' ' + str(nacq - 1))
            # this nacq-1 is bad. Because Laser Wavelength DI would already be created, this is the easy solution.
            if mode == 'middle': data_item.define_property("title",
                                                           mode + str(npic) + '_det' + str(i) + ' ' + str(nacq - 1))

            if show: self.event_loop.create_task(self.data_item_show(data_item))

    def call_monitor(self):
        self.pow02_mon_array = numpy.zeros(200)
        self.pow02_mon_di = DataItemCreation("Power Fiber", self.pow02_mon_array, 1, [0], [1], ['time (arb. units)'])
        self.event_loop.create_task(self.data_item_show(self.pow02_mon_di.data_item))

    def append_monitor_data(self, value, index):
        power02 = value
        if index==0:
            self.pow02_mon_array = numpy.zeros(200)
        self.pow02_mon_array[index] = power02
        self.pow02_mon_di.fast_update_data_only(self.pow02_mon_array)

    def call_data(self, nacq, pts, avg, start, end, step, cam_acq, **kwargs):

        if len(cam_acq.data.shape) > 1:
            cam_pixels = cam_acq.data.shape[1]
            cam_calibration = cam_acq.get_dimensional_calibration(1)
        else:
            cam_pixels = cam_acq.data.shape[0]
            cam_calibration = cam_acq.get_dimensional_calibration(0)

        self.cam_array = numpy.zeros((pts * avg, cam_pixels))
        self.avg = avg
        self.pts = pts

        for data_items in self.document_controller.document_model._DocumentModel__data_items:
            if data_items.title == 'Gain Data ' + str(nacq):
                nacq += 1

        # Power Meter call
        self.pow02_array = numpy.zeros(pts * avg)
        self.pow02_di = DataItemCreation("Power 02 " + str(nacq), self.pow02_array, 1, [0], [1], ['uW'])

        # CAMERA CALL
        if start == end and step == 0.0:
            self.cam_di = DataItemCreation('Gain Data ' + str(nacq), self.cam_array, 2,
                                           [0, cam_calibration.offset], [1 / avg, cam_calibration.scale],
                                           ['nm', 'eV'], title='Gain Data ' + str(nacq), start_wav=start, end_wav=end,
                                           pts=pts, averages=avg, step_wav=step, **kwargs)
        else:
            self.cam_di = DataItemCreation('Gain Data ' + str(nacq), self.cam_array, 2,
                                           [start, cam_calibration.offset], [step / avg, cam_calibration.scale],
                                           ['nm', 'eV'], title='Gain Data ' + str(nacq), start_wav=start, end_wav=end,
                                           pts=pts, averages=avg, step_wav=step, **kwargs)
        self.event_loop.create_task(self.data_item_show(self.cam_di.data_item))

    def append_data(self, value, index1, index2, camera_data, update=True):

        if len(camera_data.data.shape)>1:
            cam_hor = numpy.sum(camera_data.data, axis=0)
        else:
            cam_hor = camera_data.data

        power02 = value
        self.pow02_array[index2 + index1 * self.avg] = power02
        self.cam_array[index2 + index1 * self.avg] = cam_hor  # Get raw data

        if update: self.cam_di.update_data_only(self.cam_array)

    def end_data_monitor(self):
        if self.pow02_mon_di:
            self.event_loop.create_task(self.data_item_exit_live(self.pow02_mon_di.data_item))

    def end_data(self):
        if self.pow02_di:
            self.event_loop.create_task(self.data_item_show(self.pow02_di.data_item))
            self.event_loop.create_task(self.data_item_exit_live(self.pow02_di.data_item))
        if self.cam_di: self.event_loop.create_task(self.data_item_exit_live(self.cam_di.data_item))

    def stop_function(self, wiget):
        self.instrument.Laser_stop_all()


class gainView:

    def __init__(self, instrument: gain_inst.gainDevice):
        ui = Declarative.DeclarativeUI()

        self.server_ping_pb = ui.create_push_button(text="Server Ping", name="server_ping_pb",
                                                    on_clicked="server_ping_push")
        self.init_pb = ui.create_push_button(text="Init All", name="init_pb", on_clicked="init_push")
        self.host_label = ui.create_label(text='Host: ')
        self.host_value = ui.create_line_edit(name='host_value', text='@binding(instrument.host_f)')
        self.port_label = ui.create_label(text = 'Port: ')
        self.port_value = ui.create_line_edit(name='port_value', text='@binding(instrument.port_f)')
        self.server_label = ui.create_label(text='Server: ')
        self.server_value = ui.create_label(name='server_value', text='OFF')
        self.server_choice = ui.create_combo_box(items=['Local Host', 'VG Lumiere', 'Raspberry Pi'], on_current_index_changed='server_choice_pick')
        self.server_shutdown = ui.create_push_button(name='server_shutdown', text='Shutdown', on_clicked='server_shutdown_push')
        self.init_row = ui.create_row(self.server_ping_pb, self.init_pb, self.host_label, self.host_value,
                                      self.port_label, self.port_value, self.server_label, self.server_value, self.server_choice, ui.create_stretch(), self.server_shutdown, spacing=12)

        self.start_label = ui.create_label(text='Start Wavelength (nm): ')
        self.start_line = ui.create_line_edit(text="@binding(instrument.start_wav_f)", name="start_line", width=100)
        self.pts_label = ui.create_label(text='E-points: ')
        self.pts_value_label = ui.create_label(text="@binding(instrument.pts_f)")
        self.ui_view1 = ui.create_row(self.start_label, self.start_line, ui.create_stretch(), self.pts_label,
                                      self.pts_value_label, spacing=12)

        self.finish_label = ui.create_label(text='Finish Wavelength (nm): ')
        self.finish_line = ui.create_line_edit(text="@binding(instrument.finish_wav_f)", name="finish_line", width=100)
        self.tpts_label = ui.create_label(text='Total points: ')
        self.tpts_value_label = ui.create_label(text='@binding(instrument.tpts_f)')
        self.ui_view2 = ui.create_row(self.finish_label, self.finish_line, ui.create_stretch(), self.tpts_label,
                                      self.tpts_value_label, spacing=12)

        self.step_label = ui.create_label(text='Step Wavelength (nm): ')
        self.step_line = ui.create_line_edit(text="@binding(instrument.step_wav_f)", name="step_line", width=100)
        self.current_label = ui.create_label(text='Current Wavelength (nm): ')
        self.current_value_label = ui.create_label(text='@binding(instrument.cur_wav_f)')
        self.ui_view3 = ui.create_row(self.step_label, self.step_line, ui.create_stretch(), self.current_label,
                                      self.current_value_label, spacing=12)

        self.avg_label = ui.create_label(text='Averages: ')
        self.avg_line = ui.create_line_edit(text="@binding(instrument.avg_f)", name="avg_line", width=100)
        self.running_label = ui.create_label(text='Is running? ')
        self.running_value_label = ui.create_label(text='@binding(instrument.run_status_f)')
        self.ui_view4 = ui.create_row(self.avg_label, self.avg_line, ui.create_stretch(), self.running_label,
                                      self.running_value_label, spacing=12)

        self.laser_group = ui.create_group(title='Sirah Credo', content=ui.create_column(
            self.ui_view1, self.ui_view2, self.ui_view3, self.ui_view4)
                                           )

        self.power_label = ui.create_label(text='Power (uW): ')
        self.auto_power_lock = ui.create_check_box(name='auto_powe_lock', text='Auto Lock', checked='@binding(instrument.auto_lock_f)')
        self.power_value_label = ui.create_label(text="@binding(instrument.power_f)")
        self.power_lock_button = ui.create_push_button(text='Lock Current Power', name='Lock_power',
                                                       on_clicked='lock_push')
        self.power_row00 = ui.create_row(self.power_label, self.power_value_label, ui.create_stretch(),
                                         self.auto_power_lock, self.power_lock_button)
        self.power_lock_label = ui.create_label(text='Control Power (uW): ')
        self.power_lock_value = ui.create_label(text='@binding(instrument.locked_power_f)')
        self.power_row01 = ui.create_row(self.power_lock_label, self.power_lock_value, ui.create_stretch())
        self.pm2_label = ui.create_label(text='Power 02 (uW): ')
        self.power02_value_label = ui.create_label(text="@binding(instrument.power02_f)")
        self.power_row02 = ui.create_row(self.pm2_label, self.power02_value_label, ui.create_stretch())
        self.trans_label = ui.create_label(text='Transmission: ')
        self.trans_value = ui.create_label(text='@binding(instrument.power_transmission_f)')
        self.power_row03 = ui.create_row(self.trans_label, self.trans_value, ui.create_stretch(), spacing=12)
        self.power_avg_label = ui.create_label(text='Number of Averages: ')
        self.power_avg_value = ui.create_line_edit(name='power_avg_value', text='@binding(instrument.powermeter_avg_f)', width=100)
        self.power_reset_button = ui.create_push_button(text='Hard Reset', name='power_reset_button',
                                                        on_clicked='pw_hard_reset')
        self.power_row04 = ui.create_row(self.power_avg_label, self.power_avg_value, ui.create_stretch(),
                                         self.power_reset_button)

        self.powermeter_group = ui.create_group(title='ThorLabs PowerMeter', content=ui.create_column(
            self.power_row00, self.power_row01, self.power_row02, self.power_row03, self.power_row04)
                                                )

        self.diode_checkbox = ui.create_check_box(text='Diodes', name="diode_checkbox",
                                                  checked='@binding(instrument.d_f)')
        self.q_checkbox = ui.create_check_box(text='Q Switch', name="q_checkbox", checked='@binding(instrument.q_f)')
        self.control_label = ui.create_label(text="Control: ")
        self.control_list = ui.create_combo_box(items=['None', 'Servo', 'Laser PS'],
                                                current_index='@binding(instrument.pw_ctrl_type_f)',
                                                name='control_list')
        self.shutter_pb = ui.create_push_button(text='Shutter', name="sht_pb", on_clicked='sht_push')
        self.ui_view8 = ui.create_row(self.diode_checkbox,
                                      ui.create_stretch(), self.q_checkbox,
                                      ui.create_stretch(), self.control_label, self.control_list, ui.create_stretch(),
                                      self.shutter_pb, spacing=12)

        self.diode_cur_label = ui.create_label(text='Current 01: ')
        self.diode_cur_value_label = ui.create_label(name='diode_cur_value_label', text="@binding(instrument.cur_d1_f)")
        self.diode_cur2_label = ui.create_label(text='Current 02: ')
        self.diode_cur2_value_label = ui.create_label(name='diode_cur2_value_label', text='@binding(instrument.cur_d2_f)')
        self.shutter_label02 = ui.create_label(text='Shutter: ')
        self.shutter_label02_value = ui.create_label(text='@binding(instrument.sht_f)')

        self.ui_view9 = ui.create_row(self.diode_cur_label, self.diode_cur_value_label, self.diode_cur2_label,
                                      self.diode_cur2_value_label, ui.create_stretch(), self.shutter_label02,
                                      self.shutter_label02_value, spacing=12)

        self.diode_cur_label = ui.create_label(text='Diode(1, 2) (A): ')
        self.diode_cur_slider = ui.create_slider(name="cur_slider", value='@binding(instrument.cur_d_f)', minimum=0,
                                                 maximum=int(30 * 100))
        self.text_label = ui.create_label(text='       ||       ')
        self.diode_cur_line = ui.create_line_edit(text='@binding(instrument.cur_d_edit_f)', name='cur_line', width=100)
        self.less_pb = ui.create_push_button(text="<<", name="less_pb", on_clicked="less_push", width=25)
        self.more_pb = ui.create_push_button(text=">>", name="more_pb", on_clicked="more_push", width=25)
        self.tdc_send = ui.create_check_box(text='Line5 to TDC1', name="tdc_send", checked='@binding(instrument.tdc_f)')
        self.ui_view10 = ui.create_row(self.diode_cur_label, self.diode_cur_slider, self.text_label,
                                       ui.create_spacing(12), self.less_pb, ui.create_spacing(5),
                                       self.more_pb, ui.create_stretch(), self.tdc_send)

        self.diode1_temp_label = ui.create_label(text='T1 (°C): ')
        self.diode1_temp_value = ui.create_label(text='@binding(instrument.t_d1_f)')
        self.diode2_temp_label = ui.create_label(text='T2 (°C): ')
        self.diode2_temp_value = ui.create_label(text='@binding(instrument.t_d2_f)')
        self.ui_view11 = ui.create_row(self.diode1_temp_label, self.diode1_temp_value, self.diode2_temp_label,
                                       self.diode2_temp_value, ui.create_stretch(), spacing=12)

        self.ps_group = ui.create_group(title='Laser PS', content=ui.create_column(
            self.ui_view8,
            self.ui_view9, self.ui_view10, self.ui_view11)
                                        )
        # Servo Motor

        self.servo_label = ui.create_label(text='Angle: ')
        self.servo_slider = ui.create_slider(name="servo_slider", value='@binding(instrument.servo_f)', minimum=0,
                                             maximum=180)
        self.less_servo_pb = ui.create_push_button(text="<<", name="less_servo_pb", on_clicked="less_servo_push",
                                                   width=25)
        self.more_servo_pb = ui.create_push_button(text=">>", name="more_servo_pb", on_clicked="more_servo_push",
                                                   width=25)
        self.current_servo_label = ui.create_label(text='Current: ')
        self.current_servo_value = ui.create_label(text='@binding(instrument.servo_f)')
        self.servo_wobbler_cb = ui.create_check_box(text='Wobbler Servo', name='servo_wobbler_cb',
                                                    checked='@binding(instrument.servo_wobbler_f)')

        self.servo_row = ui.create_row(self.servo_label, self.servo_slider, self.less_servo_pb, self.more_servo_pb,
                                       self.current_servo_label, self.current_servo_value, ui.create_stretch(),
                                       self.servo_wobbler_cb, spacing=12)

        self.servo_step_label = ui.create_label(text='Servo Step (°): ')
        self.servo_step_value = ui.create_line_edit(name='servo_step_value', text='@binding(instrument.servo_step_f)', width=100)
        self.servo_p_points_label = ui.create_label(text='P-Points: ')
        self.servo_p_points_value = ui.create_label(text='@binding(instrument.servo_pts_f)')
        self.servo_step_row = ui.create_row(self.servo_step_label, self.servo_step_value, self.servo_p_points_label,
                                            self.servo_p_points_value, ui.create_stretch(), spacing=12)

        self.servo_group = ui.create_group(title='Servo Motor', content=ui.create_column(
            self.servo_row, self.servo_step_row))

        # Fast Blanker
        self.delay_label = ui.create_label(text='Delay (ns): ')
        self.delay_value = ui.create_line_edit(name='delay_value', text='@binding(instrument.laser_delay_f)', width=100)
        self.delay_slider = ui.create_slider(name='delay_slider', value='@binding(instrument.laser_delay_f)',
                                             minimum=600, maximum=1200)
        self.delay_row = ui.create_row(self.delay_label, self.delay_value, self.text_label, self.delay_slider,
                                       ui.create_stretch())

        self.width_label = ui.create_label(text='Width (ns): ')
        self.width_value = ui.create_line_edit(name='width_value', text='@binding(instrument.laser_width_f)', width=100)
        self.frequency_label = ui.create_label(text='Frequency (Hz): ')
        self.frequency_value = ui.create_line_edit(name='frequency_value',
                                                   text='@binding(instrument.laser_frequency_f)', width=100)
        self.width_row = ui.create_row(self.width_label, self.width_value, ui.create_spacing(12),
                                       self.frequency_label, self.frequency_value, ui.create_stretch())

        self.stop_pb = ui.create_push_button(name='stop_pb', text='Stop All', on_clicked='stop_function')
        self.fast_blanker_checkbox = ui.create_check_box(name='fast_blanker_checkbox',
                                                         checked='@binding(instrument.fast_blanker_status_f)',
                                                         text='Shoot')
        self.counts_label = ui.create_label(text='Counts: ')
        self.counts_value = ui.create_label(text='@binding(instrument.laser_counts_f)')

        self.hv_label = ui.create_label(text='Voltage (V):')
        self.hv_value = ui.create_line_edit(name='hv_slider', text='@binding(instrument.hv_f)', width=50)


        self.hv_label_ratio = ui.create_label(text='HV Ratio:')
        self.hv_slider_ratio = ui.create_slider(name='hv_slider_ratio', minimum=-100, maximum=100, width=150,
                                          value='@binding(instrument.hv_ratio_f)')

        self.final_row = ui.create_row(self.fast_blanker_checkbox,
                                       ui.create_spacing(25), self.counts_label, self.counts_value,
                                       ui.create_spacing(25), self.stop_pb, ui.create_stretch(),
                                       self.hv_label, ui.create_spacing(10),
                                       self.hv_value, ui.create_spacing(50))

        self.hv_ratio_row = ui.create_row(ui.create_stretch(), self.hv_label_ratio, ui.create_spacing(10),
                                          self.hv_slider_ratio, ui.create_spacing(25))

        self.blanker_group = ui.create_group(title='Fast Blanker / HV Control', content=ui.create_column(
            self.delay_row, self.width_row, self.final_row, self.hv_ratio_row)
                                             )

        ## ACQUISTION BUTTONS

        self.upt_pb = ui.create_push_button(text="Update", name="upt_pb", on_clicked="upt_push", width=150)
        self.acq_pb = ui.create_push_button(text="Acquire", name="acq_pb", on_clicked="acq_push", width=150)
        self.mon_pb = ui.create_push_button(text='Monitor Power', name="mon_pb", on_clicked="mon_push", width=150)
        self.abt_pb = ui.create_push_button(text="Abort", name="abt_pb", on_clicked="abt_push", width=150)

        self.buttons_row00 = ui.create_row(self.upt_pb, self.acq_pb, self.mon_pb, self.abt_pb, ui.create_stretch(), spacing=12)

        self.power_ramp_pb = ui.create_push_button(text='Servo Scan', name='pr_pb', on_clicked="acq_pr_push", width=150)
        self.acq_trans_pb = ui.create_push_button(text="Acquire Transmission", name="acq_trans_pb", on_clicked="acq_trans_push", width=150)
        self.periodic_pics_checkbox = ui.create_check_box(name='periodic_pics_checkbox',
                                                          checked='@binding(instrument.per_pic_f)',
                                                          on_check_state_changed='change_periodic_pic',
                                                          text='Periodic DET?')
        self.periodic_pics_label = ui.create_label(text='How many (per acq.): ')
        self.periodic_pics_value = ui.create_line_edit(name='periodic_pics_value',
                                                       text='@binding(instrument.many_per_pic_f)', width=100)
        self.buttons_row01 = ui.create_row(self.power_ramp_pb, self.acq_trans_pb, self.periodic_pics_checkbox, self.periodic_pics_label,
                                           self.periodic_pics_value, ui.create_stretch(), spacing=12)

        self.buttons_group = ui.create_group(title='Acquisition', content=ui.create_column(
            self.buttons_row00, self.buttons_row01))
        ## END FIRST TAB

        self.ui_view = ui.create_column(
            self.init_row, self.laser_group, self.powermeter_group, self.ps_group, self.servo_group, self.blanker_group,
            self.buttons_group)

def create_spectro_panel(document_controller, panel_id, properties):
    instrument = properties["instrument"]
    ui_handler = gainhandler(instrument, document_controller)
    ui_view = gainView(instrument)
    panel = Panel.Panel(document_controller, panel_id, properties)

    finishes = list()
    panel.widget = Declarative.construct(document_controller.ui, None, ui_view.ui_view, ui_handler, finishes)

    for finish in finishes:
        finish()
    if ui_handler and hasattr(ui_handler, "init_handler"):
        ui_handler.init_handler()
    return panel


def run(instrument: gain_inst.gainDevice) -> None:
    panel_id = "Laser"  # make sure it is unique, otherwise only one of the panel will be displayed
    name = _("Laser")
    Workspace.WorkspaceManager().register_panel(create_spectro_panel, panel_id, name, ["left", "right"], "left",
                                                {"instrument": instrument})
