# standard libraries
import gettext
from nion.swift import Panel
from nion.swift import Workspace

from nion.ui import Declarative
from nion.ui import UserInterface
from nion.data import Calibration
from nion.data import DataAndMetadata
from nion.swift.model import HardwareSource
from nion.swift.model import DataItem
from nion.swift.model import Utility

from . import gain_inst
from . import gain_data
import numpy
import os
import json
import logging
import numpy

_ = gettext.gettext

abs_path = os.path.abspath(os.path.join((__file__ + "/../"), "global_settings.json"))
with open(abs_path) as savfile:
    settings = json.load(savfile)

MAX_CURRENT = settings["PS"]["MAX_CURRENT"]


class DataItemLaserCreation():
    def __init__(self, title, array, which, start=None, final=None, pts=None, avg=None, step=None, delay=None,
                 time_width=None, start_ps_cur=None, ctrl=None, is_live=True, eels_dispersion=1.0, hor_pixels=1600,
                 oversample=1, power_min=0, power_inc=1, power_array_itp=None):
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
            "control": ctrl
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
        if which == 'ALIGNED_CAM_DATA':
            self.dimensional_calibrations = [Calibration.Calibration(), Calibration.Calibration()]
            self.dimensional_calibrations[0].units = 'nm'
            self.dimensional_calibrations[0].offset = start
            self.dimensional_calibrations[0].scale = step
            self.dimensional_calibrations[1].units = 'eV'
            self.dimensional_calibrations[1].scale = eels_dispersion
            self.dimensional_calibrations[1].offset = -hor_pixels / 2. * eels_dispersion
        if which == 'SMOOTHED_DATA':
            self.dimensional_calibrations = [Calibration.Calibration(), Calibration.Calibration()]
            self.dimensional_calibrations[0].units = 'nm'
            self.dimensional_calibrations[0].offset = start
            self.dimensional_calibrations[0].scale = step
            self.dimensional_calibrations[1].units = 'eV'
            self.dimensional_calibrations[1].scale = eels_dispersion / oversample
            self.dimensional_calibrations[1].offset = -hor_pixels / 2. * eels_dispersion

        self.xdata = DataAndMetadata.new_data_and_metadata(array, self.calibration, self.dimensional_calibrations,
                                                           timezone=self.timezone, timezone_offset=self.timezone_offset)

        self.data_item = DataItem.DataItem()
        self.data_item.set_xdata(self.xdata)
        self.data_item.define_property("title", title)
        self.data_item.define_property("description", self.acq_parameters)
        self.data_item.define_property("caption", self.acq_parameters)

        if is_live: self.data_item._enter_live_state()

    def update_data_only(self, array: numpy.array):
        self.xdata = DataAndMetadata.new_data_and_metadata(array, self.calibration, self.dimensional_calibrations,
                                                           timezone=self.timezone, timezone_offset=self.timezone_offset)
        self.data_item.set_xdata(self.xdata)

    def set_cam_di_calibration(self, calib: Calibration.Calibration()):
        self.dimensional_calibrations[1] = calib


class gainhandler:

    def __init__(self, instrument: gain_inst.gainDevice, document_controller):

        self.event_loop = document_controller.event_loop
        self.document_controller = document_controller
        self.instrument = instrument
        self.enabled = False
        self.__camera_hardware = HardwareSource.HardwareSourceManager().hardware_sources[0]
        self.busy_event_listener = self.instrument.busy_event.listen(self.prepare_widget_disable)
        self.property_changed_event_listener = self.instrument.property_changed_event.listen(self.prepare_widget_enable)
        self.free_event_listener = self.instrument.free_event.listen(self.prepare_free_widget_enable)

        self.call_data_listener = self.instrument.call_data.listen(self.call_data)
        self.append_data_listener = self.instrument.append_data.listen(self.append_data)
        self.end_data_listener = self.instrument.end_data.listen(self.end_data)

        self.server_shutdown_listener = self.instrument.server_shutdown.listen(self.server_shut)

        self.det_acq_listener = self.instrument.det_acq.listen(self.show_det)

        self.__current_DI = None
        self.__current_DI_POW = None
        self.__current_DI_WAV = None

        self.data_proc = gain_data.gainData()

        self.wav_di = None
        self.pow_di = None
        self.pow02_di = None
        self.ser_di = None
        self.ps_di = None
        self.trans_di = None
        self.cam_di = None
        self.aligned_cam_di = None

        self.current_acquition = None

    def init_handler(self):
        self.event_loop.create_task(self.do_enable(True, ['']))
        self.event_loop.create_task(self.do_enable(False, ['init_pb', 'server_ping_push', 'host_value', 'port_value',
                                                           'server_value', 'server_choice']))  # not working as something is calling this guy
        self.normalize_check_box.checked = False  # in process_data
        self.normalize_current_check_box.checked = True
        self.display_check_box.checked = True
        self.savgol_window_value.text = '3'
        self.savgol_poly_order_value.text = '1'
        self.savgol_oversample_value.text = '1'
        self.many_replicas.text = '4'
        self.tolerance_energy_value.text = '0.00'

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
            elif self.host_value.text == '192.168.137.96':
                self.server_value.text = 'Raspberry π'
            else:
                self.server_value.text = 'User-Defined'
            self.event_loop.create_task(
                self.do_enable(True, ['init_pb', 'plot_power_wav', 'align_zlp_max', 'align_zlp_fit', 'smooth_zlp',
                                  'process_eegs_pb',
                                  'process_power_pb', 'fit_pb',
                                  'cancel_pb']))  # not working as something is
        # calling this guy
            self.actions_list = [self.plot_power_wav, self.align_zlp_max, self.align_zlp_fit, self.smooth_zlp,
                             self.process_eegs_pb,
                             self.process_power_pb, self.fit_pb,
                             self.cancel_pb]  # i can put here because GUI was already initialized


    def server_choice_pick(self, widget, current_index):
        if current_index == 0:
            self.host_value.text = '127.0.0.1'
            self.port_value.text = '65432'
        if current_index == 1:
            self.host_value.text = '129.175.82.159'
            self.port_value.text = '65432'
        if current_index == 2:
            self.host_value.text = '192.168.137.96'
            self.port_value.text = '65432'
        if current_index == 3:
            self.host_value.text = '1.0.0.1'
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

    #Transmission Tab
    def acq_trans_push(self, widget):
        self.instrument.acq_trans()

    def acq_pr_push(self, widget):
        self.instrument.acq_pr()

    def abt_push(self, widget):
        self.instrument.abt()

    #Transmission Tab
    def abt_trans_push(self, widget):
        pass

    def sht_push(self, widget):
        self.instrument.sht()

    def lock_push(self, widget):
        self.instrument.lock()

    def pw_hard_reset(self, widget):
        self.instrument.hard_reset()

    def dio_check(self, widget, checked):
        self.instrument.diode(checked)

    def q_check(self, widget, checked):
        self.instrument.q(checked)

    def more_push(self, widget):
        self.instrument.cur_d_f += 5

    def less_push(self, widget):
        self.instrument.cur_d_f -= 5

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

    def show_dye(self, widget):

        if self.dye_value.current_index == 0:
            abs_path = os.path.abspath(os.path.join((__file__ + "/../Dyes"), "Pyrromethene_597.json"))
            with open(abs_path) as savfile:
                pyr_597 = json.load(savfile)

            spatial_calibs = pyr_597["spatial_calibrations"][0]

            abs_path = os.path.abspath(os.path.join((__file__ + "/../Dyes"), "Pyrromethene_597.npy"))
            array_597 = numpy.load(abs_path)
            di_597 = DataItemLaserCreation('Pyrromethene 597', array_597, "power_as_wav",
                                           spatial_calibs["offset"], None, None,
                                           None, spatial_calibs["scale"], None,
                                           None, None,
                                           None, is_live=False)

            self.event_loop.create_task(self.data_item_show(di_597.data_item))

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

    def call_data(self, nacq, pts, avg, start, end, step, ctrl, delay, width, diode_cur, trans=0):
        if self.current_acquition != nacq:
            self.__adjusted = False
            self.current_acquition = nacq
            self.avg = avg
            self.start_wav = start
            self.end_wav = end
            self.ctrl = ctrl
            self.pts = pts
            self.step = step
            self.cam_pixels = 1600
            self.wav_array = numpy.zeros(pts * avg)
            self.pow_array = numpy.zeros(pts * avg)
            self.pow02_array = numpy.zeros(pts * avg)
            self.trans_array = numpy.zeros(pts)
            if self.ctrl == 1: self.ser_array = numpy.zeros(pts * avg)
            if self.ctrl == 2: self.ps_array = numpy.zeros(pts * avg)

            for data_items in self.document_controller.document_model._DocumentModel__data_items:
                if data_items.title == 'Laser Wavelength ' + str(nacq):
                    nacq += 1

            #while self.document_controller.document_model.get_data_item_by_title(
            #        'Laser Wavelength ' + str(nacq)) is not None:
            #    nacq += 1  # this puts always a new set even if swift crashes and counts perfectly

            self.wav_di = DataItemLaserCreation("Laser Wavelength " + str(nacq), self.wav_array, "WAV")
            self.pow_di = DataItemLaserCreation("Power " + str(nacq), self.pow_array, "POW")
            self.pow02_di = DataItemLaserCreation("Power 02 " + str(nacq), self.pow02_array, "POW")
            self.trans_di = DataItemLaserCreation("Transmission " + str(nacq), self.trans_array, "transmission_as_wav",
                                                  start, end, pts, avg, step, delay, width, diode_cur, ctrl)
            if self.ctrl == 1: self.ser_di = DataItemLaserCreation("Servo Angle " + str(nacq), self.ser_array, "SER")
            if self.ctrl == 2: self.ps_di = DataItemLaserCreation("Power Supply " + str(nacq), self.ps_array, "PS")

            self.event_loop.create_task(self.data_item_show(self.wav_di.data_item))
            self.event_loop.create_task(self.data_item_show(self.pow_di.data_item))
            if self.ctrl == 2: self.event_loop.create_task(self.data_item_show(self.ps_di.data_item))
            if self.ctrl == 1: self.event_loop.create_task(self.data_item_show(self.ser_di.data_item))
            if trans: self.event_loop.create_task(self.data_item_show(self.pow02_di.data_item))
            if trans: self.event_loop.create_task(self.data_item_show(self.trans_di.data_item))

            # CAMERA CALL
            self.cam_array = numpy.zeros((pts * avg, self.cam_pixels))
            self.cam_di = DataItemLaserCreation('Gain Data ' + str(nacq), self.cam_array, "CAM_DATA", start, end, pts,
                                                avg, step, delay, width, diode_cur, ctrl)
            if not trans: self.event_loop.create_task(self.data_item_show(self.cam_di.data_item))

    def append_data(self, value, index1, index2, camera_data):
        try:
            cur_wav, power, control, power02 = value
        except:
            cur_wav, power, power02 = value

        self.wav_array[index2 + index1 * self.avg] = cur_wav
        self.pow_array[index2 + index1 * self.avg] = power
        self.pow02_array[index2 + index1 * self.avg] = power02
        self.trans_array[index1] += (power02 / (self.instrument.rt_f * power) ) / self.avg

        if not self.__adjusted and camera_data:

            if camera_data.data.shape[1]==1:
                self.cam_pixels = camera_data.data.shape[0]
            else:
                self.cam_pixels = camera_data.data.shape[1]

            cam_calibration = camera_data.get_dimensional_calibration(0)

            if self.cam_pixels != self.cam_array.shape[1]:
                self.cam_array = numpy.zeros((self.pts * self.avg, self.cam_pixels))
                logging.info('***ACQUISITION***: Corrected #PIXELS.')
            try:
                self.cam_di.set_cam_di_calibration(cam_calibration)
                logging.info('***ACQUISITION***: Calibration OK.')
            except:
                logging.info(
                    '***ACQUISITION***: Calibration could not be done. Check if camera has get_dimensional_calibration.')

            self.__adjusted = True

        if camera_data: #if it is false, as in transmission, do nothing
            cam_hor = numpy.sum(camera_data.data, axis=0)
            self.cam_array[index2 + index1 * self.avg] = cam_hor  # Get raw data

        if self.ctrl == 1: self.ser_array[index2 + index1 * self.avg] = control
        if self.ctrl == 2: self.ps_array[index2 + index1 * self.avg] = control

        self.wav_di.update_data_only(self.wav_array)
        self.pow_di.update_data_only(self.pow_array)
        self.pow02_di.update_data_only(self.pow02_array)
        self.trans_di.update_data_only(self.trans_array)
        if camera_data: self.cam_di.update_data_only(self.cam_array)
        if self.ctrl == 1: self.ser_di.update_data_only(self.ser_array)
        if self.ctrl == 2: self.ps_di.update_data_only(self.ps_array)

    def end_data(self):
        if self.wav_di: self.event_loop.create_task(self.data_item_exit_live(self.wav_di.data_item))
        if self.pow_di: self.event_loop.create_task(self.data_item_exit_live(self.pow_di.data_item))
        if self.pow02_di: self.event_loop.create_task(self.data_item_exit_live(self.pow02_di.data_item))
        if self.trans_di: self.event_loop.create_task(self.data_item_exit_live(self.trans_di.data_item))
        if self.ser_di: self.event_loop.create_task(self.data_item_exit_live(self.ser_di.data_item))
        if self.ps_di: self.event_loop.create_task(self.data_item_exit_live(self.ps_di.data_item))
        if self.cam_di: self.event_loop.create_task(self.data_item_exit_live(self.cam_di.data_item))

    def stop_function(self, wiget):
        self.instrument.Laser_stop_all()

    def grab_data_item(self, widget):
        try:
            #self.__current_DI = self.document_controller.document_model.get_data_item_by_title(
            #    self.file_name_value.text)

            for data_items in self.document_controller.document_model._DocumentModel__data_items:
                if data_items.title == self.file_name_value.text:
                    self.__current_DI = data_items
            for pbs in self.actions_list:
                pbs.enabled = False
        except:
            pass
        if self.__current_DI:
            temp_acq = int(self.file_name_value.text[-2:])  # Works from 0-99.
            self.file_UUID_value.text = str(self.__current_DI.uuid)
            self.file_dim_value.text = str(self.__current_DI.data.ndim)
            self.file_x_disp_value.text = str(self.__current_DI.dimensional_calibrations[1].scale) + ' ' + \
                                          self.__current_DI.dimensional_calibrations[1].units
            self.zlp_value.text = ''
            self.energy_window_value.text = ''

            try:
                self.file_type_value.text = str(self.__current_DI.description['which'])
                self.pts_detected_value.text = str(self.__current_DI.description['pts'])
                self.avg_detected_value.text = str(self.__current_DI.description['averages'])
                self.start_detected_value.text = format(self.__current_DI.description['start_wav'], '.3f')
                self.final_detected_value.text = format(self.__current_DI.description['final_wav'], '.3f')
                self.step_detected_value.text = format(self.__current_DI.description['step_wav'], '.3f')
            except:
                self.file_type_value.text = 'Unknown'
                self.pts_detected_value.text = 'Unknown'
                self.avg_detected_value.text = 'Unknown'
                self.start_detected_value.text = 'Unknown'
                self.final_detected_value.text = 'Unknown'
                self.step_detected_value.text = 'Unknown'

            if "Gain" in self.file_name_value.text:
                for data_items in self.document_controller.document_model._DocumentModel__data_items:
                    if data_items.title == "Power " + str(temp_acq):
                        self.__current_DI = data_items
                    elif data_items.title == 'Laser Wavelength " + str(temp_acq)':
                        self.__current_DI_WAV = data_items

                #self.__current_DI_POW = self.document_controller.document_model.get_data_item_by_title(
                #    "Power " + str(temp_acq))
                self.power_file_detected_value.text = bool(self.__current_DI_POW)
                #self.__current_DI_WAV = self.document_controller.document_model.get_data_item_by_title(
                #    "Laser Wavelength " + str(temp_acq))
                self.wav_file_detected_value.text = bool(self.__current_DI_WAV)
                if self.__current_DI_POW and self.__current_DI_WAV:
                    self.align_zlp_max.enabled = self.plot_power_wav.enabled = True
                    self.align_zlp_fit.enabled = False  # fit not yet implemented

            elif "Power" in self.file_name_value.text:
                pass  # something to do with only power?
            elif "Wavelength" in self.file_name_value.text:
                pass  # something to do with only laser wavelength?
        else:
            logging.info('***ACQUISTION***: Could not find referenced Data Item.')

    def power_wav(self, widget):
        temp_dict = self.__current_DI.description
        pwav = numpy.reshape(self.__current_DI_POW.data,
                             (temp_dict['pts'], temp_dict['averages']))  # reshaped power array
        pwav_avg = numpy.zeros(temp_dict['pts'] - 1)  # reshaped power array averaged

        for i in range(temp_dict['pts'] - 1):
            pwav_avg[i] = numpy.average(pwav[i]) - numpy.average(pwav[-1])

        power_avg = DataItemLaserCreation('Avg_Power_' + temp_dict['title'], pwav_avg, "power_as_wav",
                                          temp_dict['start_wav'], temp_dict['final_wav'], temp_dict['pts'],
                                          temp_dict['averages'], temp_dict['step_wav'], temp_dict['delay'],
                                          temp_dict['time_width'], temp_dict['start_ps_cur'],
                                          temp_dict['control'], is_live=False)

        self.plot_power_wav.enabled = False
        self.event_loop.create_task(self.data_item_show(power_avg.data_item))
        logging.info('***ACQUISITION***: Average Power Data Item Created.')

    def align_zlp(self, widget):
        temp_dict = self.__current_DI.description
        if not temp_dict:
            temp_dict = dict()
            logging.info('***ACQUISITION***: Data Item dictionary incomplete. Please enter number of points ('
                         'including last off laser one): ')
            temp_dict['pts'] = int(input())
            self.pts_detected_value.text = temp_dict['pts']
            logging.info('***ACQUISITION***: Data Item dictionary incomplete. Please enter number of averages: ')
            temp_dict['averages'] = int(input())
            self.avg_detected_value.text = temp_dict['averages']
            logging.info('***ACQUISITION***: Data Item dictionary incomplete. Please enter start wavelength: ')
            temp_dict['start_wav'] = float(input())
            self.start_detected_value.text = format(temp_dict['start_wav'], '.3f')
            logging.info('***ACQUISITION***: Data Item dictionary incomplete. Please enter final wavelength: ')
            temp_dict['final_wav'] = float(input())
            self.final_detected_value.text = format(temp_dict['final_wav'], '.3f')
            logging.info('***ACQUISITION***: Data Item dictionary incomplete. Please enter step wavelength: ')
            temp_dict['step_wav'] = float(input())
            self.step_detected_value.text = format(temp_dict['step_wav'], '.3f')
            logging.info('***ACQUISITION***: Data Item dictionary incomplete. Please enter original title: ')
            temp_dict['title'] = input()
            # as we dont have this, we certainly dont have delay, width and control. We put it here none so we dont
            # conflict when creating data_item, as we would like to save this info if it is available
            temp_dict['delay'] = None
            temp_dict['time_width'] = None
            temp_dict['start_ps_cur'] = None
            temp_dict['control'] = None

        print(temp_dict)

        temp_data = self.__current_DI.data
        cam_pixels = len(self.__current_DI.data[0])
        eels_dispersion = self.__current_DI.dimensional_calibrations[1].scale
        temp_title_name = 'Aligned_'  # keep adding stuff as far as you doing (or not doing) stuff with your data.

        if self.normalize_current_check_box.checked:
            for i in range(len(self.__current_DI.data)):
                temp_data[i] = numpy.divide(temp_data[i], numpy.sum(temp_data[i]))
        else:
            temp_title_name += 'No_cur_'

        # ## HERE IS THE DATA PROCESSING. PTS AND AVERAGES ARE VERY IMPORTANT. OTHER ATRIBUTES ARE MOSTLY IMPORTANT
        # FOR CALIBRATION ***
        if widget == self.align_zlp_max:
            self.aligned_cam_array, zlp_fwhm, energy_window = self.data_proc.align_zlp(temp_data, temp_dict['pts'],
                                                                                       temp_dict['averages'],
                                                                                       cam_pixels,
                                                                                       eels_dispersion, 'max')
            # temp_title_name += 'max_' #we have only way to align by now

        elif widget == self.align_zlp_fit:
            pass  # not yet implemented

        # here is the window of the fitting of the ZLP with no laser ON
        self.energy_window_value.text = format(energy_window, '.3f') + ' eV'

        self.zlp_fwhm = zlp_fwhm
        self.zlp_value.text = format(zlp_fwhm, '.3f') + ' ' + self.__current_DI.dimensional_calibrations[
            1].units  # displaying
        temp_title_name += temp_dict['title']  # Final name of Data_Item

        self.aligned_cam_di = DataItemLaserCreation(temp_title_name, self.aligned_cam_array, "ALIGNED_CAM_DATA",
                                                    temp_dict['start_wav'], temp_dict['final_wav'], temp_dict['pts'],
                                                    temp_dict['averages'], temp_dict['step_wav'], temp_dict['delay'],
                                                    temp_dict['time_width'], temp_dict['start_ps_cur'],
                                                    temp_dict['control'], is_live=False,
                                                    eels_dispersion=eels_dispersion, hor_pixels=cam_pixels)

        if self.aligned_cam_di and self.zlp_fwhm:  # you free next step if the precedent one works. For the next
            # step, we need the data and FWHM
            self.smooth_zlp.enabled = True
            self.align_zlp_max.enabled = self.align_zlp_fit.enabled = self.plot_power_wav.enabled = False
            logging.info('***ACQUISITION***: Data Item created.')

        if self.display_check_box.checked: self.event_loop.create_task(self.data_item_show(self.aligned_cam_di.data_item))

    def smooth_data(self, widget):
        temp_data = self.aligned_cam_di.data_item.data

        # for the sake of comprehension, note that self.aligned_cam_di.acq_parameters is the same as
        # self.aligned_cam_di.data_item_description. acq_parameters are defined at __init__ of my
        # DataItemLaserCreation while description is a data_item property defined by nionswift. So if you wanna acess
        # these informations anywhere in any computer you need to use data_item because this is stored in nionswift
        # library.
        '''
        Produces the same output:
            print(self.aligned_cam_di.acq_parameters)
            print(self.aligned_cam_di.data_item.description)
        '''

        temp_dict = self.aligned_cam_di.data_item.description
        temp_calib = self.aligned_cam_di.data_item.dimensional_calibrations

        cam_pixels = len(self.__current_DI.data[0])
        eels_dispersion = self.__current_DI.dimensional_calibrations[1].scale
        temp_title_name = 'Smooth'

        x = numpy.arange(temp_calib[1].offset, temp_calib[1].offset + temp_calib[1].scale * temp_data[0].shape[0],
                         temp_calib[1].scale)

        try:
            window_size, poly_order = int(self.savgol_window_value.text), int(self.savgol_poly_order_value.text)
            oversample = int(self.savgol_oversample_value.text)
        except:
            window_size, poly_order, oversample = 41, 3, 10
            logging.info(
                '***ACQUISTION***: Window, Poly Order and Oversample must be integers. Using standard (41, 3, '
                '10) values.')

        temp_title_name += '_ws_' + str(window_size) + '_po_' + str(poly_order) + '_os_' + str(oversample) + '_' + \
                           temp_dict['title']

        xx = numpy.linspace(x.min(), x.max(), temp_data[0].shape[0] * oversample)

        self.smooth_array = self.data_proc.smooth_zlp(temp_data, window_size, poly_order, oversample, x, xx)

        self.smooth_di = DataItemLaserCreation(temp_title_name, self.smooth_array, "SMOOTHED_DATA",
                                               temp_dict['start_wav'], temp_dict['final_wav'], temp_dict['pts'],
                                               temp_dict['averages'], temp_dict['step_wav'], temp_dict['delay'],
                                               temp_dict['time_width'], temp_dict['start_ps_cur'],
                                               temp_dict['control'], is_live=False,
                                               eels_dispersion=eels_dispersion, hor_pixels=cam_pixels,
                                               oversample=oversample)

        if self.smooth_di:  # you free next step if smooth is OK
            if temp_dict['step_wav']:  # this means step is not zero. If step is zero then we have a power measurement.
                self.process_eegs_pb.enabled = True
            else:  # power measurement. Normalize makes no sense because we cant normalize by power here.
                self.process_power_pb.enabled = True
                self.normalize_check_box.enabled = False
            self.smooth_zlp.enabled = False
            logging.info('***ACQUISITION***: Smooth Successful. Data Item created.')

        if self.display_smooth_check_box.checked: self.event_loop.create_task(self.data_item_show(self.smooth_di.data_item))

    def process_data(self, widget):

        temp_data = self.smooth_di.data_item.data
        temp_dict = self.smooth_di.data_item.description
        temp_calib = self.smooth_di.data_item.dimensional_calibrations
        temp_gain_title_name = 'sEEGS'
        temp_loss_title_name = 'sEELS'
        temp_zlp_title_name = 'zlp'
        try:
            number_orders = int(self.many_replicas.text)
        except:
            number_orders = 1
            logging.info(
                '***ACQUISITION***: Number of replicas must be an integer. Using single-order analysis instead.')

        gain_array = numpy.zeros((number_orders, temp_dict['pts'] - 1))
        loss_array = numpy.zeros((number_orders, temp_dict['pts'] - 1))
        zlp_array = numpy.zeros(temp_dict['pts'] - 1)

        energies_loss = numpy.zeros((number_orders, temp_dict['pts'] - 1))
        energies_gain = numpy.zeros((number_orders, temp_dict['pts'] - 1))

        wavs = numpy.linspace(temp_dict['start_wav'], temp_dict['final_wav'], temp_dict['pts'] - 1)
        for k in range(number_orders):
            energies_loss[k] = numpy.divide(1239.8 * (k + 1), wavs)
            energies_gain[k] = numpy.multiply(numpy.divide(1239.8 * (k + 1), wavs), -1)

        ihp = int(round(self.zlp_fwhm / temp_calib[1].scale / 2.))  # index half peak
        cpl = numpy.array(numpy.divide(numpy.subtract(energies_loss, temp_calib[1].offset), temp_calib[1].scale),
                          dtype=int)  # center peak loss
        cpl_meas = numpy.zeros((number_orders, temp_dict['pts'] - 1), dtype=int)
        cpg = numpy.array(numpy.divide(numpy.subtract(energies_gain, temp_calib[1].offset), temp_calib[1].scale),
                          dtype=int)  # center peak gain
        cpg_meas = numpy.zeros((number_orders, temp_dict['pts'] - 1), dtype=int)

        rpa = numpy.reshape(self.__current_DI_POW.data,
                            (temp_dict['pts'], temp_dict['averages']))  # reshaped power array
        self.rpa_avg = numpy.zeros(temp_dict['pts'] - 1)  # reshaped power array averaged

        for k in range(number_orders):
            for i in range(len(temp_data) - 1):
                # here we find maximum and minimum of gain and loss based on index.
                cpg_meas[k][i] = int(
                    numpy.where(temp_data[i] == numpy.max(temp_data[i][cpg[k][i] - ihp:cpg[k][i] + ihp]))[0])
                cpl_meas[k][i] = int(
                    numpy.where(temp_data[i] == numpy.max(temp_data[i][cpl[k][i] - ihp:cpl[k][i] + ihp]))[0])

        for k in range(number_orders):
            for i in range(len(temp_data) - 1):  # excluding last point because laser is off
                garray = temp_data[i][cpg[k][i] - ihp:cpg[k][i] + ihp]
                larray = temp_data[i][cpl[k][i] - ihp:cpl[k][i] + ihp]
                if not k: zlpi = int((cpg[k][i] + cpl[k][i]) / 2)  # zlp_index. Must be close to half if its aligned
                if not k: zlparray = temp_data[i][zlpi - ihp:zlpi + ihp]  # do this when k==0 to save time

                gain_array[k][i] = numpy.sum(garray)
                loss_array[k][i] = numpy.sum(larray)
                if not k: zlp_array[i] = numpy.sum(zlparray)  # do this when k==0 to save time

                self.rpa_avg[i] = numpy.average(rpa[i]) - numpy.average(rpa[-1])

                # garray = temp_data[i][cpg_meas[k][i] - ihp:cpl_meas[k][i] + ihp]
                # gdi = DataItemLaserCreation("Laser Wavelength "+str(i)+str(k), garray, "WAV", is_live=False)
                # self.document_controller.document_model.append_data_item(gdi.data_item)

        temp_gain_title_name += '_order_' + temp_dict['title']
        temp_loss_title_name += '_order_' + temp_dict['title']
        temp_zlp_title_name += '_order_' + temp_dict['title']

        if widget == self.process_eegs_pb:
            for k in range(number_orders):

                if self.normalize_check_box.checked:
                    gain_array[k] = numpy.divide(gain_array[k], self.rpa_avg)
                    loss_array[k] = numpy.divide(loss_array[k], self.rpa_avg)
                    if not k: zlp_array = numpy.divide(zlp_array, self.rpa_avg)
                    logging.info('***ACQUISITION***: Data Normalized by power.')

                self.gain_di = DataItemLaserCreation('_' + str(k + 1) + '_' + temp_gain_title_name, gain_array[k],
                                                     "sEEGS/sEELS", temp_dict['start_wav'],
                                                     temp_dict['final_wav'], temp_dict['pts'], temp_dict['averages'],
                                                     temp_dict['step_wav'], temp_dict['delay'],
                                                     temp_dict['time_width'], temp_dict['start_ps_cur'],
                                                     temp_dict['control'], is_live=False)

                self.loss_di = DataItemLaserCreation('_' + str(k + 1) + '_' + temp_loss_title_name, loss_array[k],
                                                     "sEEGS/sEELS", temp_dict['start_wav'],
                                                     temp_dict['final_wav'], temp_dict['pts'], temp_dict['averages'],
                                                     temp_dict['step_wav'], temp_dict['delay'],
                                                     temp_dict['time_width'], temp_dict['start_ps_cur'],
                                                     temp_dict['control'], is_live=False)

                if not k: self.zlp_di = DataItemLaserCreation('_' + str(k) + '_' + temp_zlp_title_name, zlp_array,
                                                              "sEEGS/sEELS", temp_dict['start_wav'],
                                                              temp_dict['final_wav'], temp_dict['pts'],
                                                              temp_dict['averages'],
                                                              temp_dict['step_wav'], temp_dict['delay'],
                                                              temp_dict['time_width'], temp_dict['start_ps_cur'],
                                                              temp_dict['control'], is_live=False)

                self.event_loop.create_task(self.data_item_show(self.gain_di.data_item))
                self.event_loop.create_task(self.data_item_show(self.loss_di.data_item))
                if not k: self.event_loop.create_task(self.data_item_show(self.zlp_di.data_item))
            logging.info('***ACQUISITION***: sEEGS/sEELS Done.')

        if widget == self.process_power_pb:
            for k in range(number_orders):

                if not k:  # only when k==0 to save time
                    power_array_itp, zlp_array_itp, power_inc = self.data_proc.as_power_func(zlp_array, self.rpa_avg)
                    self.zlp_di = DataItemLaserCreation('Power_' + str(k) + '_' + temp_gain_title_name, zlp_array_itp,
                                                        "sEEGS/sEELS_power", temp_dict['start_wav'],
                                                        temp_dict['final_wav'], temp_dict['pts'], temp_dict['averages'],
                                                        temp_dict['step_wav'], temp_dict['delay'],
                                                        temp_dict['time_width'], temp_dict['start_ps_cur'],
                                                        temp_dict['control'], is_live=False,
                                                        power_min=power_array_itp.min(), power_inc=power_inc)

                    self.event_loop.create_task(self.data_item_show(self.zlp_di.data_item))

                power_array_itp, gain_array_itp, power_inc = self.data_proc.as_power_func(gain_array[k], self.rpa_avg)
                self.gain_di = DataItemLaserCreation('Power_' + str(k + 1) + '_' + temp_gain_title_name, gain_array_itp,
                                                     "sEEGS/sEELS_power", temp_dict['start_wav'],
                                                     temp_dict['final_wav'], temp_dict['pts'], temp_dict['averages'],
                                                     temp_dict['step_wav'], temp_dict['delay'],
                                                     temp_dict['time_width'], temp_dict['start_ps_cur'],
                                                     temp_dict['control'], is_live=False,
                                                     power_min=power_array_itp.min(), power_inc=power_inc)

                self.event_loop.create_task(self.data_item_show(self.gain_di.data_item))

                power_array_itp, loss_array_itp, power_inc = self.data_proc.as_power_func(loss_array[k], self.rpa_avg)
                self.loss_di = DataItemLaserCreation('Power_' + str(k + 1) + '_' + temp_loss_title_name, loss_array_itp,
                                                     "sEEGS/sEELS_power", temp_dict['start_wav'],
                                                     temp_dict['final_wav'], temp_dict['pts'], temp_dict['averages'],
                                                     temp_dict['step_wav'], temp_dict['delay'],
                                                     temp_dict['time_width'], temp_dict['start_ps_cur'],
                                                     temp_dict['control'], is_live=False,
                                                     power_min=power_array_itp.min(), power_inc=power_inc)
                self.event_loop.create_task(self.data_item_show(self.loss_di.data_item))

                logging.info('***ACQUISTION***: Power Scan Done.')

        self.process_eegs_pb.enabled = False
        self.process_power_pb.enabled = False
        if self.gain_di and self.loss_di and self.smooth_di:
            self.fit_pb.enabled = True
            if widget == self.process_power_pb: self.fit_pb.text = 'Fit Power Scan'
            if widget == self.process_eegs_pb: self.fit_pb.text = 'Fit Laser Scan'
        self.cancel_pb.enabled = True

    def fit_or_cancel(self, widget):

        temp_data = self.smooth_di.data_item.data
        temp_dict = self.smooth_di.data_item.description
        temp_calib = self.smooth_di.data_item.dimensional_calibrations

        data_size = temp_data.shape[1]
        eels_dispersion = - 2 * temp_calib[1].offset / data_size
        oversample = eels_dispersion / temp_calib[1].scale

        wavs = numpy.linspace(temp_dict['start_wav'], temp_dict['final_wav'], temp_dict['pts'] - 1)
        energies_loss = numpy.divide(1239.8, wavs)
        tol = float(self.tolerance_energy_value.text)

        if widget == self.fit_pb:

            try:
                number_orders = int(self.many_replicas.text)
                if number_orders > 4:
                    number_orders = 4
                    logging.info('***ACQUISITION***: Maximum number of orders is 4. Using 4 instead.')
            except:
                number_orders = 1
                logging.info(
                    '***ACQUISITION***: Number of replicas must be an integer. Using single-order analysis instead.')
            logging.info('***ACQUISITION***: Attempting to fit data..')

            # fit array is the fitting data from smooth, a_array is the intensity of the zlp, a1_array is the intensity
            # of the first replica, a2_array is the intensity of the second replica and sigma_array is the sigma
            # that can be used to check for FWHM

            fit_array, a_array, a1_array, a2_array, a3_array, a4_array, sigma_array, ene_array = self.data_proc.fit_data(
                temp_data,
                temp_dict['pts'],
                temp_dict[
                    'start_wav'],
                temp_dict[
                    'final_wav'],
                temp_dict[
                    'step_wav'],
                temp_calib[1].scale,
                self.zlp_fwhm,
                number_orders, tol)

            self.fit_di = DataItemLaserCreation('fit_' + temp_dict['title'], fit_array, "SMOOTHED_DATA",
                                                temp_dict['start_wav'], temp_dict['final_wav'], temp_dict['pts'],
                                                temp_dict['averages'], temp_dict['step_wav'], temp_dict['delay'],
                                                temp_dict['time_width'], temp_dict['start_ps_cur'],
                                                temp_dict['control'], is_live=False,
                                                eels_dispersion=eels_dispersion, hor_pixels=data_size,
                                                oversample=oversample)

            self.event_loop.create_task(self.data_item_show(self.fit_di.data_item))

            if self.fit_pb.text == 'Fit Laser Scan':

                if self.normalize_check_box.checked:
                    a_array = numpy.divide(a_array[:-1], self.rpa_avg)
                    a1_array = numpy.divide(a1_array[:-1], self.rpa_avg)
                    a2_array = numpy.divide(a2_array[:-1], self.rpa_avg)
                    a3_array = numpy.divide(a3_array[:-1], self.rpa_avg)
                    a4_array = numpy.divide(a4_array[:-1], self.rpa_avg)
                    logging.info('***ACQUISITION***: Data Normalized by power.')

                self.int_di = DataItemLaserCreation('_fit_int_' + temp_dict['title'], a_array[:-1],
                                                    "sEEGS/sEELS", temp_dict['start_wav'],
                                                    temp_dict['final_wav'], temp_dict['pts'], temp_dict['averages'],
                                                    temp_dict['step_wav'], temp_dict['delay'],
                                                    temp_dict['time_width'], temp_dict['start_ps_cur'],
                                                    temp_dict['control'], is_live=False)

                self.int1_di = DataItemLaserCreation('_fit_int1_' + temp_dict['title'], a1_array[:-1],
                                                     "sEEGS/sEELS", temp_dict['start_wav'],
                                                     temp_dict['final_wav'], temp_dict['pts'], temp_dict['averages'],
                                                     temp_dict['step_wav'], temp_dict['delay'],
                                                     temp_dict['time_width'], temp_dict['start_ps_cur'],
                                                     temp_dict['control'], is_live=False)

                self.int2_di = DataItemLaserCreation('_fit_int2_' + temp_dict['title'], a2_array[:-1],
                                                     "sEEGS/sEELS", temp_dict['start_wav'],
                                                     temp_dict['final_wav'], temp_dict['pts'], temp_dict['averages'],
                                                     temp_dict['step_wav'], temp_dict['delay'],
                                                     temp_dict['time_width'], temp_dict['start_ps_cur'],
                                                     temp_dict['control'], is_live=False)

                self.int3_di = DataItemLaserCreation('_fit_int3_' + temp_dict['title'], a3_array[:-1],
                                                     "sEEGS/sEELS", temp_dict['start_wav'],
                                                     temp_dict['final_wav'], temp_dict['pts'], temp_dict['averages'],
                                                     temp_dict['step_wav'], temp_dict['delay'],
                                                     temp_dict['time_width'], temp_dict['start_ps_cur'],
                                                     temp_dict['control'], is_live=False)

                self.int4_di = DataItemLaserCreation('_fit_int4_' + temp_dict['title'], a4_array[:-1],
                                                     "sEEGS/sEELS", temp_dict['start_wav'],
                                                     temp_dict['final_wav'], temp_dict['pts'], temp_dict['averages'],
                                                     temp_dict['step_wav'], temp_dict['delay'],
                                                     temp_dict['time_width'], temp_dict['start_ps_cur'],
                                                     temp_dict['control'], is_live=False)

            if self.fit_pb.text == 'Fit Power Scan':
                power_array_itp, a_array_itp, power_inc = self.data_proc.as_power_func(a_array[:-1], self.rpa_avg)
                self.int_di = DataItemLaserCreation('Power_fit_int_' + temp_dict['title'], a_array_itp,
                                                    "sEEGS/sEELS_power", temp_dict['start_wav'],
                                                    temp_dict['final_wav'], temp_dict['pts'], temp_dict['averages'],
                                                    temp_dict['step_wav'], temp_dict['delay'],
                                                    temp_dict['time_width'], temp_dict['start_ps_cur'],
                                                    temp_dict['control'], is_live=False,
                                                    power_min=power_array_itp.min(), power_inc=power_inc)

                power_array_itp, a1_array_itp, power_inc = self.data_proc.as_power_func(a1_array[:-1], self.rpa_avg)
                self.int1_di = DataItemLaserCreation('Power_fit_int1_' + temp_dict['title'], a1_array_itp,
                                                     "sEEGS/sEELS_power", temp_dict['start_wav'],
                                                     temp_dict['final_wav'], temp_dict['pts'], temp_dict['averages'],
                                                     temp_dict['step_wav'], temp_dict['delay'],
                                                     temp_dict['time_width'], temp_dict['start_ps_cur'],
                                                     temp_dict['control'], is_live=False,
                                                     power_min=power_array_itp.min(), power_inc=power_inc)

                power_array_itp, a2_array_itp, power_inc = self.data_proc.as_power_func(a2_array[:-1], self.rpa_avg)
                self.int2_di = DataItemLaserCreation('Power_fit_int2_' + temp_dict['title'], a2_array_itp,
                                                     "sEEGS/sEELS_power", temp_dict['start_wav'],
                                                     temp_dict['final_wav'], temp_dict['pts'], temp_dict['averages'],
                                                     temp_dict['step_wav'], temp_dict['delay'],
                                                     temp_dict['time_width'], temp_dict['start_ps_cur'],
                                                     temp_dict['control'], is_live=False,
                                                     power_min=power_array_itp.min(), power_inc=power_inc)

                power_array_itp, a3_array_itp, power_inc = self.data_proc.as_power_func(a3_array[:-1], self.rpa_avg)
                self.int3_di = DataItemLaserCreation('Power_fit_int3_' + temp_dict['title'], a3_array_itp,
                                                     "sEEGS/sEELS_power", temp_dict['start_wav'],
                                                     temp_dict['final_wav'], temp_dict['pts'], temp_dict['averages'],
                                                     temp_dict['step_wav'], temp_dict['delay'],
                                                     temp_dict['time_width'], temp_dict['start_ps_cur'],
                                                     temp_dict['control'], is_live=False,
                                                     power_min=power_array_itp.min(), power_inc=power_inc)

                power_array_itp, a4_array_itp, power_inc = self.data_proc.as_power_func(a4_array[:-1], self.rpa_avg)
                self.int4_di = DataItemLaserCreation('Power_fit_int4_' + temp_dict['title'], a4_array_itp,
                                                     "sEEGS/sEELS_power", temp_dict['start_wav'],
                                                     temp_dict['final_wav'], temp_dict['pts'], temp_dict['averages'],
                                                     temp_dict['step_wav'], temp_dict['delay'],
                                                     temp_dict['time_width'], temp_dict['start_ps_cur'],
                                                     temp_dict['control'], is_live=False,
                                                     power_min=power_array_itp.min(), power_inc=power_inc)

            self.event_loop.create_task(self.data_item_show(self.int_di.data_item))
            if a1_array.any(): self.event_loop.create_task(self.data_item_show(self.int1_di.data_item))
            if a2_array.any(): self.event_loop.create_task(self.data_item_show(self.int2_di.data_item))
            if a3_array.any(): self.event_loop.create_task(self.data_item_show(self.int3_di.data_item))
            if a4_array.any(): self.event_loop.create_task(self.data_item_show(self.int4_di.data_item))

            logging.info('***ACQUISITION***: Fit Done.')

        elif widget == self.cancel_pb:
            logging.info('***ACQUISITION***: Not attempting to fit data.')

        for pbs in self.actions_list:
            pbs.enabled = False
        self.aligned_cam_di = None  # kill this attribute so next one will start from the beg. Safest way to do it.
        self.smooth_di = None  # kill this one as well.
        self.zlp_fwhm = None  # kill ZLP as well
        self.gain_di = None  # too bad, you dead
        self.loss_di = None  # dead
        self.__current_DI_POW = None  # bye
        self.garray = None
        self.larray = None


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
        self.server_choice = ui.create_combo_box(items=['Local Host', 'VG Lumiere', 'Raspberry Pi', 'User-Defined'], on_current_index_changed='server_choice_pick')
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
        self.power_value_label = ui.create_label(text="@binding(instrument.power_f)")
        self.power_lock_button = ui.create_push_button(text='Lock Current Power', name='Lock_power',
                                                       on_clicked='lock_push')
        self.power_row00 = ui.create_row(self.power_label, self.power_value_label, ui.create_stretch(),
                                         self.power_lock_button)
        self.power_lock_label = ui.create_label(text='Control Power (uW): ')
        self.power_lock_value = ui.create_label(text='@binding(instrument.locked_power_f)')
        self.power_row01 = ui.create_row(self.power_lock_label, self.power_lock_value, ui.create_stretch())
        self.pm2_label = ui.create_label(text='Power 02 (uW): ')
        self.power02_value_label = ui.create_label(text="@binding(instrument.power02_f)")
        self.pm1_factor_label = ui.create_label(text='[R]/T Factor for PM1: ')
        self.pm1_factor_value = ui.create_line_edit(name='pm1_factor_value', text='@binding(instrument.rt_f)', width=100)
        self.power_row02 = ui.create_row(self.pm2_label, self.power02_value_label, ui.create_stretch(),
                                         self.pm1_factor_label, self.pm1_factor_value)
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

        self.diode_label = ui.create_label(text='Diodes: ')
        self.diode_checkbox = ui.create_check_box(name="diode_checkbox", on_checked_changed='dio_check')
        self.diode_value_label = ui.create_label(text="@binding(instrument.d_f)")
        self.q_label = ui.create_label(text='Q Switch: ')
        self.q_checkbox = ui.create_check_box(name="q_checkbox", on_checked_changed='q_check')
        self.q_value_label = ui.create_label(text='@binding(instrument.q_f)')
        self.control_label = ui.create_label(text="Control: ")
        self.control_list = ui.create_combo_box(items=['None', 'Servo', 'Laser PS'],
                                                current_index='@binding(instrument.pw_ctrl_type_f)',
                                                name='control_list')
        self.shutter_pb = ui.create_push_button(text='Shutter', name="sht_pb", on_clicked='sht_push')
        self.ui_view8 = ui.create_row(self.diode_label, self.diode_checkbox, self.diode_value_label,
                                      ui.create_stretch(), self.q_label, self.q_checkbox, self.q_value_label,
                                      ui.create_stretch(), self.control_label, self.control_list, ui.create_stretch(),
                                      self.shutter_pb, spacing=12)

        self.diode_cur_label = ui.create_label(text='Current 01: ')
        self.diode_cur_value_label = ui.create_label(text="@binding(instrument.cur_d1_f)")
        self.diode_cur2_label = ui.create_label(text='Current 02: ')
        self.diode_cur2_value_label = ui.create_label(text='@binding(instrument.cur_d2_f)')
        self.shutter_label02 = ui.create_label(text='Shutter: ')
        self.shutter_label02_value = ui.create_label(text='@binding(instrument.sht_f)')

        self.ui_view9 = ui.create_row(self.diode_cur_label, self.diode_cur_value_label, self.diode_cur2_label,
                                      self.diode_cur2_value_label, ui.create_stretch(), self.shutter_label02,
                                      self.shutter_label02_value, spacing=12)

        self.diode_cur_label = ui.create_label(text='Diode(1, 2) (A): ')
        self.diode_cur_slider = ui.create_slider(name="cur_slider", value='@binding(instrument.cur_d_f)', minimum=0,
                                                 maximum=int(MAX_CURRENT * 100))
        self.text_label = ui.create_label(text='       ||       ')
        self.diode_cur_line = ui.create_line_edit(text='@binding(instrument.cur_d_edit_f)', name='cur_line', width=100)
        self.less_pb = ui.create_push_button(text="<<", name="less_pb", on_clicked="less_push", width=25)
        self.more_pb = ui.create_push_button(text=">>", name="more_pb", on_clicked="more_push", width=25)
        self.ui_view10 = ui.create_row(self.diode_cur_label, self.diode_cur_slider, self.text_label,
                                       self.diode_cur_line, ui.create_spacing(12), self.less_pb, ui.create_spacing(5),
                                       self.more_pb, ui.create_stretch())

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

        self.dye_label = ui.create_label(text='Select Dye: ')
        self.dye_value = ui.create_combo_box(items=['Pyrromethene 597', 'Pyrromethene 580'],
                                             current_index='@binding(instrument.dye_f)', name='dye_value')
        self.dye_show_button = ui.create_push_button(name='dye_show_button', text='Show Dye', on_clicked='show_dye')
        self.dye_row = ui.create_row(self.dye_label, self.dye_value, self.dye_show_button, ui.create_stretch(),
                                     spacing=12)

        self.servo_group = ui.create_group(title='Servo Motor', content=ui.create_column(
            self.servo_row, self.servo_step_row, self.dye_row))

        # Fast Blanker
        self.delay_label = ui.create_label(text='Delay (ns): ')
        self.delay_value = ui.create_line_edit(name='delay_value', text='@binding(instrument.laser_delay_f)', width=100)
        self.delay_slider = ui.create_slider(name='delay_slider', value='@binding(instrument.laser_delay_f)',
                                             minimum=1740, maximum=1850)
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

        self.final_row = ui.create_row(self.fast_blanker_checkbox,
                                       ui.create_spacing(25), self.counts_label, self.counts_value,
                                       ui.create_spacing(25), self.stop_pb, ui.create_stretch())

        self.blanker_group = ui.create_group(title='Fast Blanker', content=ui.create_column(
            self.delay_row, self.width_row, self.final_row)
                                             )

        ## ACQUISTION BUTTONS

        self.upt_pb = ui.create_push_button(text="Update", name="upt_pb", on_clicked="upt_push", width=150)
        self.acq_pb = ui.create_push_button(text="Acquire", name="acq_pb", on_clicked="acq_push", width=150)
        self.abt_pb = ui.create_push_button(text="Abort", name="abt_pb", on_clicked="abt_push", width=150)

        self.buttons_row00 = ui.create_row(self.upt_pb, self.acq_pb, self.abt_pb, ui.create_stretch(), spacing=12)

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

        self.main_tab = ui.create_tab(label='Main', content=ui.create_column(
            self.init_row, self.laser_group, self.powermeter_group, self.ps_group, self.servo_group, self.blanker_group,
            self.buttons_group))

        ### BEGIN MY SECOND TAB ##

        self.grab_pb = ui.create_push_button(text='Grab', name='grab_pb', on_clicked='grab_data_item')
        self.plot_power_wav = ui.create_push_button(text='Plot Pw-Wl', name='plot_power_wav', on_clicked='power_wav')
        self.pb_row = ui.create_row(self.grab_pb, self.plot_power_wav, ui.create_stretch())

        self.file_name_label = ui.create_label(text='Title:', name='file_name_label')
        self.file_name_value = ui.create_line_edit(name='file_name_value', width=150)
        self.file_type_label = ui.create_label(text='Type: ', name='file_type_label')
        self.file_type_value = ui.create_label(text='type?', name='file_type_value')
        self.file_name_row = ui.create_row(self.file_name_label, self.file_name_value, ui.create_stretch(),
                                           self.file_type_label, self.file_type_value, ui.create_stretch())

        self.file_UUID_label = ui.create_label(text='UUID: ', name='file_UUID_label')
        self.file_UUID_value = ui.create_label(text='uuid?', name='file_UUID_value')
        self.file_dim_label = ui.create_label(text='Dim.: ', name='file_dim_label')
        self.file_dim_value = ui.create_label(text='dim?', name='file_dim_value')
        self.file_x_disp_label = ui.create_label(text='Dispersion: ', name='file_x_disp_label')
        self.file_x_disp_value = ui.create_label(text='disp?', name='file_x_disp_value')
        self.file_info_row = ui.create_row(self.file_UUID_label, self.file_UUID_value, self.file_dim_label,
                                           self.file_dim_value, self.file_x_disp_label, self.file_x_disp_value,
                                           spacing=12)

        self.power_file_detected_label = ui.create_label(text='Power? ', name='power_file_detected_label')
        self.power_file_detected_value = ui.create_label(text='False', name='power_file_detected_value')
        self.wav_file_detected_label = ui.create_label(text='Wav? ', name='wav_file_detected_label')
        self.wav_file_detected_value = ui.create_label(text='False', name='wav_file_detected_value')
        self.detection_row = ui.create_row(self.power_file_detected_label, self.power_file_detected_value,
                                           ui.create_stretch(), self.wav_file_detected_label,
                                           self.wav_file_detected_value, ui.create_stretch())

        self.pts_detected_label = ui.create_label(text='Points: ', name='pts_detected_label')
        self.pts_detected_value = ui.create_label(text='pts?', name='pts_detected_value')
        self.avg_detected_label = ui.create_label(text='Averages: ', name='avg_detected_label')
        self.avg_detected_value = ui.create_label(text='avg?', name='avg_detected_value')
        self.start_detected_label = ui.create_label(text='Start Wav.: ', name='start_detected_label')
        self.start_detected_value = ui.create_label(text='st?', name='start_detected_value')
        self.final_detected_label = ui.create_label(text='End Wav.: ', name='final_detected_label')
        self.final_detected_value = ui.create_label(text='end?', name='final_detected_value')
        self.step_detected_label = ui.create_label(text='Step Wav.: ', name='step_detected_label')
        self.step_detected_value = ui.create_label(text='stp?', name='step_detected_value')

        self.first_detected_row = ui.create_row(self.pts_detected_label, self.pts_detected_value,
                                                self.avg_detected_label, self.avg_detected_value, ui.create_stretch(),
                                                spacing=12)
        self.second_detected_row = ui.create_row(self.start_detected_label, self.start_detected_value,
                                                 self.final_detected_label, self.final_detected_value,
                                                 self.step_detected_label, self.step_detected_value,
                                                 ui.create_stretch(), spacing=12)

        self.pick_group = ui.create_group(title='Pick Tool', content=ui.create_column(
            self.file_name_row, self.file_info_row, self.detection_row, self.pb_row, self.first_detected_row,
            self.second_detected_row, ui.create_stretch()))

        self.align_zlp_max = ui.create_push_button(text='Align ZLP (Max)', on_clicked='align_zlp', name='align_zlp_max')
        self.align_zlp_fit = ui.create_push_button(text='Align ZLP (Fit)', on_clicked='align_zlp', name='align_zlp_fit')
        self.normalize_current_check_box = ui.create_check_box(text='Norm. by Current? ',
                                                               name='normalize_current_check_box')
        self.display_check_box = ui.create_check_box(text='Display?', name='display_check_box')
        self.pb_actions_row = ui.create_row(self.align_zlp_max, self.align_zlp_fit, self.normalize_current_check_box,
                                            self.display_check_box, spacing=12)

        self.zlp_label = ui.create_label(text='FWHM of ZLP: ', name='zlp_label')
        self.zlp_value = ui.create_label(text='fwhm?', name='zlp_value')
        self.energy_window = ui.create_label(text='Window (Fit): ', name='energy_window')
        self.energy_window_value = ui.create_label(text='energyW?', name='energy_window_value')
        self.zlp_row = ui.create_row(self.zlp_label, self.zlp_value, self.energy_window, self.energy_window_value,
                                     ui.create_stretch(), spacing=12)

        self.savgol_window_label = ui.create_label(text='Smoothing Window: ', name='savgol_window_label')
        self.savgol_window_value = ui.create_line_edit(name='savgol_window_value', width=100)
        self.savgol_poly_order_label = ui.create_label(text='Poly Order: ', name='savgol_poly_order_label')
        self.savgol_poly_order_value = ui.create_line_edit(name='savgol_poly_order_value', width=100)
        self.savgol_oversample_label = ui.create_label(text='Oversampling: ', name='savgol_oversample_label')
        self.savgol_oversample_value = ui.create_line_edit(name='savgol_oversample_value', width=100)
        self.savgol_row = ui.create_row(self.savgol_window_label, self.savgol_window_value,
                                        self.savgol_poly_order_label, self.savgol_poly_order_value,
                                        self.savgol_oversample_label, self.savgol_oversample_value, ui.create_stretch())

        self.smooth_zlp = ui.create_push_button(text='Smooth ZLP', on_clicked='smooth_data', name='smooth_zlp')
        self.display_smooth_check_box = ui.create_check_box(text='Display?', name='display_smooth_check_box')
        self.smooth_row = ui.create_row(self.smooth_zlp, self.display_smooth_check_box, spacing=12)

        self.process_eegs_pb = ui.create_push_button(text='Process Laser Scan', on_clicked='process_data',
                                                     name='process_eegs_pb')
        self.normalize_check_box = ui.create_check_box(text='Norm. by Power? ', name='normalize_check_box')
        self.process_power_pb = ui.create_push_button(text='Process Power Scan', on_clicked='process_data',
                                                      name='process_power_pb')
        self.many_replicas_label = ui.create_label(text='# Orders?: ')
        self.many_replicas = ui.create_line_edit(name='many_replicas', width=100)
        self.pb_process_row = ui.create_row(self.process_eegs_pb, self.process_power_pb, self.normalize_check_box,
                                            self.many_replicas_label, self.many_replicas,
                                            spacing=3)

        self.fit_pb = ui.create_push_button(text='Fit', on_clicked='fit_or_cancel', name='fit_pb')
        self.cancel_pb = ui.create_push_button(text='Cancel', on_clicked='fit_or_cancel', name='cancel_pb')
        self.tolerance_energy = ui.create_label(text='Tolerance in Energy: ')
        self.tolerance_energy_value = ui.create_line_edit(name='tolerance_energy_value', width=100)
        self.fit_row = ui.create_row(self.fit_pb, self.cancel_pb, self.tolerance_energy, self.tolerance_energy_value,
                                     ui.create_stretch(), spacing=12)

        self.actions_group = ui.create_group(title='Actions', content=ui.create_column(
            self.pb_actions_row, self.zlp_row, self.savgol_row, self.smooth_row, self.pb_process_row,
            self.fit_row, ui.create_stretch())
                                             )

        self.ana_tab = ui.create_tab(label='Analysis', content=ui.create_column(
            self.pick_group, self.actions_group, ui.create_stretch())
                                     )
        ## END ANALYSYS TAB

        self.tabs = ui.create_tabs(self.main_tab, self.ana_tab)
        self.ui_view = ui.create_column(self.tabs)

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
