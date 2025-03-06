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
        self.data_item._enter_live_state()

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

    def init_push(self, widget):
        ok = self.instrument.init()
        if ok:
            self.init_pb.enabled = False
            self.event_loop.create_task(
                self.do_enable(True, ['init_pb']))  # not working as something is
        # calling this guy

    def server_ping_push(self, widget):
        self.instrument.server_instrument_ping()

    def upt_push(self, widget):
        self.instrument.upt()

    def lock_push(self, widget):
        self.instrument.lock()

    def acq_push(self, widget):
        self.instrument.acq()

    def mon_push(self, widget):
        self.instrument.acq_mon()

    def abt_push(self, widget):
        self.instrument.abt()

    def pw_hard_reset(self, widget):
        self.instrument.hard_reset()

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
        self.pow_mon_array = numpy.zeros(200)
        self.pow02_mon_array = numpy.zeros(200)
        self.pow_mon_di = DataItemCreation("Power", self.pow_mon_array, 1, [0], [1], ['time (arb. units)'])
        self.pow02_mon_di = DataItemCreation("Power 02", self.pow02_mon_array, 1, [0], [1], ['time (arb. units)'])
        self.event_loop.create_task(self.data_item_show(self.pow_mon_di.data_item))
        self.event_loop.create_task(self.data_item_show(self.pow02_mon_di.data_item))

    def append_monitor_data(self, value, index):
        power, power02 = value
        if index==0:
            self.pow_mon_array = numpy.zeros(200)
            self.pow02_mon_array = numpy.zeros(200)
        self.pow_mon_array[index] = power
        self.pow02_mon_array[index] = power02
        self.pow_mon_di.fast_update_data_only(self.pow_mon_array)
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
        self.init_row = ui.create_row(self.server_ping_pb, self.init_pb, ui.create_stretch(), spacing=12)

        self.start_label = ui.create_label(text='Start/Central Wavelength (nm): ')
        self.start_line = ui.create_line_edit(text="@binding(instrument.start_wav_f)", name="start_line", width=75)
        self.bandwith_label = ui.create_label(text='Bandwidth (nm): ')
        self.bandwith_line = ui.create_line_edit(text="@binding(instrument.bandwidth_wav_f)", name="bandwidth_line",
                                                 width=75)
        self.pts_label = ui.create_label(text='E-points: ')
        self.pts_value_label = ui.create_label(text="@binding(instrument.pts_f)")
        self.ui_view1 = ui.create_row(self.start_label, self.start_line, ui.create_spacing(2),
                                      self.bandwith_label, self.bandwith_line,
                                      ui.create_stretch(), self.pts_label,
                                      self.pts_value_label, spacing=12)

        self.finish_label = ui.create_label(text='Finish Wavelength (nm): ')
        self.finish_line = ui.create_line_edit(text="@binding(instrument.finish_wav_f)", name="finish_line", width=75)
        self.tpts_label = ui.create_label(text='Total points: ')
        self.tpts_value_label = ui.create_label(text='@binding(instrument.tpts_f)')
        self.ui_view2 = ui.create_row(self.finish_label, self.finish_line, ui.create_stretch(), self.tpts_label,
                                      self.tpts_value_label, spacing=12)

        self.step_label = ui.create_label(text='Step Wavelength (nm): ')
        self.step_line = ui.create_line_edit(text="@binding(instrument.step_wav_f)", name="step_line", width=75)
        self.intensity_label = ui.create_label(text='Intensity (%): ')
        self.intensity_line = ui.create_line_edit(text="@binding(instrument.laser_intensity_f)", name="intensity_line", width=75)
        self.ui_view3 = ui.create_row(self.step_label, self.step_line, ui.create_stretch(),
                                      self.intensity_label, self.intensity_line,spacing=12)

        self.avg_label = ui.create_label(text='Averages: ')
        self.avg_line = ui.create_line_edit(text="@binding(instrument.avg_f)", name="avg_line", width=75)
        self.running_label = ui.create_label(text='Is running? ')
        self.running_value_label = ui.create_label(text='@binding(instrument.run_status_f)')
        self.ui_view4 = ui.create_row(self.avg_label, self.avg_line, ui.create_stretch(), self.running_label,
                                      self.running_value_label, spacing=12)

        self.emission_checkbox = ui.create_check_box(name='emission_checkbox',
                                                          checked='@binding(instrument.emission_f)',
                                                          text='Emission?')
        self.delay_label = ui.create_label(text='Delay: ')
        self.delay_line = ui.create_line_edit(text="@binding(instrument.delay_f)", name="delay_line", width=75)
        self.ui_view5 = ui.create_row(self.delay_label, self.delay_line, ui.create_stretch(),
                                      self.emission_checkbox, spacing=12)
        self.laser_group = ui.create_group(title='NKT Photonics', content=ui.create_column(
            self.ui_view1, self.ui_view2, self.ui_view3, self.ui_view4, self.ui_view5)
                                           )

        # RF Driver and SuperK Select
        self.rf_power_checkbox = ui.create_check_box(name='rf_power_checkbox',
                                                     checked='@binding(instrument.rf_power_f)',
                                                     text='RF Power?')

        self.wav0_label = ui.create_label(text='Wavelength0 (nm): ')
        self.wav0_line = ui.create_line_edit(text="@binding(instrument.wav0_f)", name="wav0_line", width=75)
        self.wav1_label = ui.create_label(text='Wavelength1 (nm): ')
        self.wav1_line = ui.create_line_edit(text="@binding(instrument.wav1_f)", name="wav1_line", width=75)
        self.wav2_label = ui.create_label(text='Wavelength2 (nm): ')
        self.wav2_line = ui.create_line_edit(text="@binding(instrument.wav2_f)", name="wav2_line", width=75)
        self.wav3_label = ui.create_label(text='Wavelength3 (nm): ')
        self.wav3_line = ui.create_line_edit(text="@binding(instrument.wav3_f)", name="wav3_line", width=75)
        self.wav4_label = ui.create_label(text='Wavelength4 (nm): ')
        self.wav4_line = ui.create_line_edit(text="@binding(instrument.wav4_f)", name="wav4_line", width=75)
        self.wav5_label = ui.create_label(text='Wavelength5 (nm): ')
        self.wav5_line = ui.create_line_edit(text="@binding(instrument.wav5_f)", name="wav5_line", width=75)
        self.wav6_label = ui.create_label(text='Wavelength6 (nm): ')
        self.wav6_line = ui.create_line_edit(text="@binding(instrument.wav6_f)", name="wav6_line", width=75)
        self.wav7_label = ui.create_label(text='Wavelength7 (nm): ')
        self.wav7_line = ui.create_line_edit(text="@binding(instrument.wav7_f)", name="wav7_line", width=75)

        self.amp0_label = ui.create_label(text='Amplitude0 (nm): ')
        self.amp0_line = ui.create_line_edit(text="@binding(instrument.amp0_f)", name="amp0_line", width=75)
        self.amp1_label = ui.create_label(text='Amplitude1 (nm): ')
        self.amp1_line = ui.create_line_edit(text="@binding(instrument.amp1_f)", name="amp1_line", width=75)
        self.amp2_label = ui.create_label(text='Amplitude2 (nm): ')
        self.amp2_line = ui.create_line_edit(text="@binding(instrument.amp2_f)", name="amp2_line", width=75)
        self.amp3_label = ui.create_label(text='Amplitude3 (nm): ')
        self.amp3_line = ui.create_line_edit(text="@binding(instrument.amp3_f)", name="amp3_line", width=75)
        self.amp4_label = ui.create_label(text='Amplitude4 (nm): ')
        self.amp4_line = ui.create_line_edit(text="@binding(instrument.amp4_f)", name="amp4_line", width=75)
        self.amp5_label = ui.create_label(text='Amplitude5 (nm): ')
        self.amp5_line = ui.create_line_edit(text="@binding(instrument.amp5_f)", name="amp5_line", width=75)
        self.amp6_label = ui.create_label(text='Amplitude6 (nm): ')
        self.amp6_line = ui.create_line_edit(text="@binding(instrument.amp6_f)", name="amp6_line", width=75)
        self.amp7_label = ui.create_label(text='Amplitude7 (nm): ')
        self.amp7_line = ui.create_line_edit(text="@binding(instrument.amp7_f)", name="amp7_line", width=75)


        self.rf_power_row = ui.create_row(self.rf_power_checkbox, ui.create_stretch())
        self.wav0_row = ui.create_row(self.wav0_label, self.wav0_line, ui.create_stretch(), self.amp0_label,
                                        self.amp0_line)
        self.wav1_row = ui.create_row(self.wav1_label, self.wav1_line, ui.create_stretch(), self.amp1_label,
                                        self.amp1_line)
        self.wav2_row = ui.create_row(self.wav2_label, self.wav2_line, ui.create_stretch(), self.amp2_label,
                                        self.amp2_line)
        self.wav3_row = ui.create_row(self.wav3_label, self.wav3_line, ui.create_stretch(), self.amp3_label,
                                        self.amp3_line)
        self.wav4_row = ui.create_row(self.wav4_label, self.wav4_line, ui.create_stretch(), self.amp4_label,
                                        self.amp4_line)
        self.wav5_row = ui.create_row(self.wav5_label, self.wav5_line, ui.create_stretch(), self.amp5_label,
                                        self.amp5_line)
        self.wav6_row = ui.create_row(self.wav6_label, self.wav6_line, ui.create_stretch(), self.amp6_label,
                                        self.amp6_line)
        self.wav7_row = ui.create_row(self.wav7_label, self.wav7_line, ui.create_stretch(), self.amp7_label,
                                        self.amp7_line)

        self.rf_group = ui.create_group(title='RF Driver', content= ui.create_column(
            self.rf_power_row, self.wav0_row, self.wav1_row, self.wav2_row, self.wav3_row, self.wav4_row, self.wav5_row,
            self.wav6_row, self.wav7_row
        ))


        # PowerMeter group
        self.power_label = ui.create_label(text='Power (uW): ')
        self.power_value_label = ui.create_label(text="@binding(instrument.power_f)")
        self.power_lock_button = ui.create_push_button(text='Lock Current Power', name='Lock_power',
                                                       on_clicked='lock_push')
        self.power_row00 = ui.create_row(self.power_label, self.power_value_label, ui.create_stretch(), self.power_lock_button)
        self.power_lock_label = ui.create_label(text='Control Power (uW): ')
        self.power_row01 = ui.create_row(self.power_lock_label, ui.create_stretch())
        self.power_avg_label = ui.create_label(text='Number of Averages: ')
        self.power_avg_value = ui.create_line_edit(name='power_avg_value', text='@binding(instrument.powermeter_avg_f)', width=100)
        self.power_reset_button = ui.create_push_button(text='Hard Reset', name='power_reset_button',
                                                        on_clicked='pw_hard_reset')
        self.power_row04 = ui.create_row(self.power_avg_label, self.power_avg_value, ui.create_stretch(),
                                         self.power_reset_button)

        self.powermeter_group = ui.create_group(title='ThorLabs PowerMeter', content=ui.create_column(
            self.power_row00, self.power_row01, self.power_row04)
                                                )

        # Fast toggling buttons
        self.defocus_label = ui.create_label(text='Defocus (nm): ')
        self.defocus_value = ui.create_line_edit(name='defocus_value', text='@binding(instrument.defocus_value_f)', width=100)
        self.defocus_checkbox = ui.create_check_box(name='defocus_checkbox',
                                                          checked='@binding(instrument.defocus_check_f)',
                                                          text='Toggle?')

        self.defocus_group = ui.create_group(title='Focus toggling', content=ui.create_column(
            ui.create_row(self.defocus_label, self.defocus_value, self.defocus_checkbox, ui.create_stretch())))

        ## ACQUISTION BUTTONS

        self.upt_pb = ui.create_push_button(text="Update", name="upt_pb", on_clicked="upt_push", width=125)
        self.acq_pb = ui.create_push_button(text="Acquire", name="acq_pb", on_clicked="acq_push", width=125)
        self.mon_pb = ui.create_push_button(text='Monitor Power', name="mon_pb", on_clicked="mon_push", width=125)
        self.abt_pb = ui.create_push_button(text="Abort", name="abt_pb", on_clicked="abt_push", width=125)

        self.buttons_row00 = ui.create_row(self.upt_pb, self.acq_pb, self.mon_pb, self.abt_pb, ui.create_stretch(), spacing=12)

        self.buttons_group = ui.create_group(title='Acquisition', content=ui.create_column(
            self.buttons_row00))
        ## END FIRST TAB

        self.ui_view = ui.create_column(
            self.init_row, self.laser_group, self.rf_group, self.powermeter_group,
            self.defocus_group, self.buttons_group)

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
    panel_id = "Laser NKT"  # make sure it is unique, otherwise only one of the panel will be displayed
    name = _("Laser NKT")
    Workspace.WorkspaceManager().register_panel(create_spectro_panel, panel_id, name, ["left", "right"], "left",
                                                {"instrument": instrument})
