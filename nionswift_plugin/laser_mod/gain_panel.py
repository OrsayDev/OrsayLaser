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
    def __init__(self, title, array, which, start=None, final = None, pts = None, avg=None, step=None, delay=None, time_width=None, start_ps_cur = None, ctrl=None, is_live=True, eels_dispersion = 1.0, hor_pixels = 1600, oversample = 1):
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
            self.calibration.units='nm'
        if which == 'POW':
            self.calibration.units = 'μW'
        if which == 'SER':
            self.calibration.units = '°'
        if which == 'PS':
            self.calibration.units = 'A'
        if which == "CAM_DATA":
            self.dimensional_calibrations = [Calibration.Calibration(), Calibration.Calibration()]
            self.dimensional_calibrations[0].units = 'nm'
            self.dimensional_calibrations[0].offset=start
            self.dimensional_calibrations[0].scale=(step)/avg
            self.dimensional_calibrations[1].units = 'eV'
        if which == 'ALIGNED_CAM_DATA':
            self.dimensional_calibrations = [Calibration.Calibration(), Calibration.Calibration()]
            self.dimensional_calibrations[0].units = 'nm'
            self.dimensional_calibrations[0].offset = start
            self.dimensional_calibrations[0].scale = step
            self.dimensional_calibrations[1].units = 'eV'
            self.dimensional_calibrations[1].scale = eels_dispersion
            self.dimensional_calibrations[1].offset = -hor_pixels/2. * eels_dispersion
        if which == 'SMOOTHED_DATA':
            self.dimensional_calibrations = [Calibration.Calibration(), Calibration.Calibration()]
            self.dimensional_calibrations[0].units = 'nm'
            self.dimensional_calibrations[0].offset = start
            self.dimensional_calibrations[0].scale = step
            self.dimensional_calibrations[1].units = 'eV'
            self.dimensional_calibrations[1].scale = eels_dispersion / oversample
            self.dimensional_calibrations[1].offset = -hor_pixels/2. * eels_dispersion


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

        # self.event_loop=event_loop #MATHIEU
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
        
        self.__current_DI = None
        self.__current_DI_POW = None
        self.__current_DI_WAV = None

        self.data_proc = gain_data.gainData()

        self.wav_di = None
        self.pow_di = None
        self.ser_di = None
        self.ps_di = None
        self.cam_di = None
        self.aligned_cam_di = None

        self.current_acquition = None

    def init_handler(self):
        self.event_loop.create_task(self.do_enable(False, ['init_pb']))  # not working as something is calling this guy
        self.normalize_check_box.checked = True
        self.normalize_current_check_box.checked = True
        self.display_check_box.checked = True
        self.savgol_window_value.text = '41'
        self.savgol_poly_order_value.text = '3'
        self.savgol_oversample_value.text = '10'

    def init_push(self, widget):
        self.instrument.init()
        self.init_pb.enabled = False
        self.event_loop.create_task(self.do_enable(True, ['init_pb', 'align_zlp_max', 'align_zlp_fit', 'smooth_zlp', 'process_eegs_pb', 'process_power_pb']))  # not working as something is calling this guy
        self.actions_list = [self.align_zlp_max, self.align_zlp_fit, self.smooth_zlp, self.process_eegs_pb, self.process_power_pb] #i can put here because GUI was already initialized

    def upt_push(self, widget):
        # self.grab()
        self.instrument.upt()

    def acq_push(self, widget):
        self.instrument.acq()
    
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

    async def do_enable(self, enabled=True, not_affected_widget_name_list=None):
        for var in self.__dict__:
            if var not in not_affected_widget_name_list:
                if isinstance(getattr(self, var), UserInterface.Widget):
                    widg = getattr(self, var)
                    setattr(widg, "enabled", enabled)

    def prepare_widget_enable(self, value):
        self.event_loop.create_task(self.do_enable(False, ["init_pb", "abt_pb"]))

    def prepare_widget_disable(self, value):
        self.event_loop.create_task(self.do_enable(False, ["init_pb"]))

    def prepare_free_widget_enable(self,
                                   value):  # THAT THE SECOND EVENT NEVER WORKS. WHAT IS THE DIF BETWEEN THE FIRST?
        self.event_loop.create_task(self.do_enable(True, ["init_pb", 'align_zlp_max']))

    def call_data(self, nacq, pts, avg, start, end, step, ctrl, delay, width, diode_cur):
        if self.current_acquition != nacq:
            self.__adjusted=False
            self.current_acquition = nacq
            self.avg = avg
            self.start_wav = start
            self.end_wav = end
            self.ctrl = ctrl
            self.pts=pts
            self.step=step
            self.cam_pixels = 1600
            self.wav_array = numpy.zeros(pts * avg)
            self.pow_array = numpy.zeros(pts * avg)
            if self.ctrl == 1: self.ser_array = numpy.zeros(pts * avg)
            if self.ctrl == 2: self.ps_array = numpy.zeros(pts * avg)
            
            while self.document_controller.document_model.get_data_item_by_title("Laser Wavelength " + str(nacq)) != None:
                nacq+=1 #this puts always a new set even if swift crashes
            
            self.wav_di = DataItemLaserCreation("Laser Wavelength " + str(nacq), self.wav_array, "WAV")
            self.pow_di = DataItemLaserCreation("Power " + str(nacq), self.pow_array, "POW")
            if self.ctrl == 1: self.ser_di = DataItemLaserCreation("Servo Angle " + str(nacq), self.ser_array, "SER")
            if self.ctrl == 2: self.ps_di = DataItemLaserCreation("Power Supply " + str(nacq), self.ps_array, "PS")

            self.document_controller.document_model.append_data_item(self.wav_di.data_item)
            self.document_controller.document_model.append_data_item(self.pow_di.data_item)
            if self.ctrl == 2: self.document_controller.document_model.append_data_item(self.ps_di.data_item)
            if self.ctrl == 1: self.document_controller.document_model.append_data_item(self.ser_di.data_item)

            # CAMERA CALL
            self.cam_array = numpy.zeros((pts * avg, self.cam_pixels))
            self.cam_di = DataItemLaserCreation('Gain Data ' + str(nacq), self.cam_array, "CAM_DATA", start, end, pts, avg, step, delay, width, diode_cur, ctrl)
            self.document_controller.document_model.append_data_item(self.cam_di.data_item)



    def append_data(self, value, index1, index2, camera_data):
        try:
            cur_wav, power, control = value
        except:
            cur_wav, power = value

        self.wav_array[index2 + index1 * self.avg] = cur_wav
        self.pow_array[index2 + index1 * self.avg] = power
        if not self.__adjusted:

            self.cam_pixels = camera_data.data.shape[1]
            cam_calibration = camera_data.get_dimensional_calibration(1)

            if camera_data.data.shape[1] != self.cam_array.shape[1]:
                self.cam_array=numpy.zeros((self.pts * self.avg, camera_data.data.shape[1]))
                logging.info('***ACQUISTION***: Corrected #PIXELS.')
            try:
                self.cam_di.set_cam_di_calibration(cam_calibration)
                logging.info('***ACQUISTION***: Calibration OK.')
            except:
                logging.info('***ACQUISTION***: Calibration could not be done. Check if camera has get_dimensional_calibration.')

            self.__adjusted=True

        cam_hor = numpy.sum(camera_data.data, axis=0)

        self.cam_array[index2 + index1 * self.avg] = cam_hor  # Get raw data

        if self.ctrl == 1: self.ser_array[index2 + index1 * self.avg] = control
        if self.ctrl == 2: self.ps_array[index2 + index1 * self.avg] = control

        self.wav_di.update_data_only(self.wav_array)
        self.pow_di.update_data_only(self.pow_array)
        self.cam_di.update_data_only(self.cam_array)
        if self.ctrl == 1: self.ser_di.update_data_only(self.ser_array)
        if self.ctrl == 2: self.ps_di.update_data_only(self.ps_array)

    def end_data(self):
        if self.wav_di: self.wav_di.data_item._exit_live_state()
        if self.pow_di: self.pow_di.data_item._exit_live_state()
        if self.ser_di: self.ser_di.data_item._exit_live_state()
        if self.ps_di: self.ps_di.data_item._exit_live_state()
        if self.cam_di: self.cam_di.data_item._exit_live_state()

    def stop_function(self, wiget):
        self.instrument.Laser_stop_all()

    def grab_data_item(self, widget):
        try:
            self.__current_DI = self.document_controller.document_model.get_data_item_by_title(self.file_name_value.text)
            for pbs in self.actions_list:
                pbs.enabled=False
        except:
            pass
        if self.__current_DI:
            temp_acq = int(self.file_name_value.text[-2:]) #Works from 0-99.
            self.file_UUID_value.text = self.__current_DI.uuid
            self.file_dim_value.text = self.__current_DI.data.ndim
            self.file_x_disp_value.text=str(self.__current_DI.dimensional_calibrations[1].scale) + ' ' + self.__current_DI.dimensional_calibrations[1].units
            try:
                self.file_type_value.text = self.__current_DI.description['which']
            except:
                self.file_type_value.text = 'Unknown'
            if "Gain" in self.file_name_value.text:
                self.__current_DI_POW = self.document_controller.document_model.get_data_item_by_title("Power " + str(temp_acq))
                self.power_file_detected_value.text = bool(self.__current_DI_POW)
                self.__current_DI_WAV = self.document_controller.document_model.get_data_item_by_title("Laser Wavelength " + str(temp_acq))
                self.wav_file_detected_value.text = bool(self.__current_DI_WAV)
                if self.__current_DI_POW and self.__current_DI_WAV:
                    self.align_zlp_max.enabled = self.align_zlp_fit.enabled = True

            elif "Power" in self.file_name_value.text:
                pass #something to do with only power?
            elif "Wavelength" in self.file_name_value.text:
                pass #something to do with only laser wavelength?
        else:
            logging.info('***ACQUISTION***: Could not find referenced Data Item.')



    def align_zlp(self, widget):
        temp_dict = self.__current_DI.description
        if not temp_dict:
            temp_dict = dict()
            logging.info('***ACQUISITION***: Data Item dictionary incomplete. Please enter number of different energies (laser scan) or servo positions (servo scan): ')
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

        else:
            self.pts_detected_value.text = temp_dict['pts']
            self.avg_detected_value.text = temp_dict['averages']
            self.start_detected_value.text = format(temp_dict['start_wav'], '.3f')
            self.final_detected_value.text = format(temp_dict['final_wav'], '.3f')
            self.step_detected_value.text = format(temp_dict['step_wav'], '.3f')

        
        temp_data = self.__current_DI.data
        cam_pixels = len(self.__current_DI.data[0])
        eels_dispersion = self.__current_DI.dimensional_calibrations[1].scale
        temp_title_name = 'Aligned' #keep adding stuff as far as you doing (or not doing) stuff with your data. Always use a temp one
    
        if self.normalize_check_box.checked:
            for i in range(len(self.__current_DI.data)-temp_dict['averages']): #excludes last str(avg) points (LASER OFF).
                temp_data[i] = numpy.divide(temp_data[i], self.__current_DI_POW.data[i])
            temp_title_name+='_Npw'

        if self.normalize_current_check_box.checked:
            for i in range(len(self.__current_DI.data)):
                temp_data[i] = numpy.divide(temp_data[i], numpy.sum(temp_data[i]))
            temp_title_name+='_Ncur'
        
        ### HERE IS THE DATA PROCESSING. PTS AND AVERAGES ARE VERY IMPORTANT. OTHER ATRIBUTES ARE MOSTLY IMPORTANT FOR CALIBRATION ***
        if widget==self.align_zlp_max:
            self.aligned_cam_array, zlp_fwhm = self.data_proc.align_zlp(temp_data, temp_dict['pts'], temp_dict['averages'], cam_pixels, eels_dispersion, 'max')
            temp_title_name+='_max'
        elif widget==self.align_zlp_fit:
            self.aligned_cam_array, zlp_fwhm = self.data_proc.align_zlp(temp_data, temp_dict['pts'], temp_dict['averages'], cam_pixels, eels_dispersion, 'fit')
            temp_title_name+='_fit'
        
        self.zlp_fwhm = zlp_fwhm
        self.zlp_value.text = format(zlp_fwhm, '.3f') + ' ' + self.__current_DI.dimensional_calibrations[1].units #displaying
        temp_title_name+=' '+temp_dict['title'] #Final name of Data_Item

        self.aligned_cam_di = DataItemLaserCreation(temp_title_name, self.aligned_cam_array, "ALIGNED_CAM_DATA", temp_dict['start_wav'], temp_dict['final_wav'], temp_dict['pts'] , temp_dict['averages'], temp_dict['step_wav'], is_live = False, eels_dispersion = eels_dispersion, hor_pixels = cam_pixels)
            
        if self.aligned_cam_di and self.zlp_fwhm: #you free next step if the precedent one works. For the next step, we need the data and FWHM
            #self.process_eegs_pb.enabled = self.process_power_pb.enabled = True
            self.smooth_zlp.enabled = True
            self.align_zlp_max.enabled = self.align_zlp_fit.enabled = False
            logging.info('***ACQUISITION***: Data Item created.')

        if self.display_check_box.checked: self.document_controller.document_model.append_data_item(self.aligned_cam_di.data_item)


    def smooth_data(self, widget):
        temp_data = self.aligned_cam_di.data_item.data

        #for the sake of comprehension, note that self.aligned_cam_di.acq_parameters is the same as self.aligned_cam_di.data_item_description. acq_parameters are defined at __init__ of my DataItemLaserCreation while description is a data_item property defined by nionswift. So if you wanna acess these informations anywhere in any computer you need to use data_item because this is stored in nionswift library. 
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

        x = numpy.arange(temp_calib[1].offset, temp_calib[1].offset + temp_calib[1].scale*temp_data[0].shape[0], temp_calib[1].scale)

        try:
            window_size, poly_order = int(self.savgol_window_value.text), int(self.savgol_poly_order_value.text)
            oversample = int(self.savgol_oversample_value.text)
        except:
            window_size, poly_order, oversample = 41, 3, 10
            logging.info('***ACQUISTION***: Window, Poly Order and Oversample must be integers. Using standard (41, 3, 10) values.')

        temp_title_name+= '_ws_'+str(window_size)+'_po_'+str(poly_order)+'_os_'+str(oversample)+'_'+temp_dict['title']
        
        xx = numpy.linspace(x.min(), x.max(), temp_data[0].shape[0] * oversample)

        self.smooth_array = self.data_proc.smooth_zlp(temp_data, window_size, poly_order, oversample, x, xx)
            
        self.smooth_di = DataItemLaserCreation(temp_title_name, self.smooth_array, "SMOOTHED_DATA", temp_dict['start_wav'], temp_dict['final_wav'], temp_dict['pts'] , temp_dict['averages'], temp_dict['step_wav'], is_live = False, eels_dispersion = eels_dispersion, hor_pixels = cam_pixels, oversample = oversample)
        
        if self.smooth_di: #you free next step if smooth is OK
            self.process_eegs_pb.enabled = self.process_power_pb.enabled = True
            self.smooth_zlp.enabled = False
            logging.info('***ACQUISITION***: Smooth Sucessfull. Data Item created.')

        if self.display_smooth_check_box.checked: self.document_controller.document_model.append_data_item(self.smooth_di.data_item)

    def process_data(self, widget):

        if widget==self.process_eegs_pb: 
            logging.info('***ACQUISTION***: EEGS Processing....')

        if widget==self.process_power_pb: 
            logging.info('***ACQUISTION***: Power Scan Processing....')
            

        for pbs in self.actions_list:
            pbs.enabled=False
        self.aligned_cam_di = None #kill this attribute so next one will start from the beginning. Safest way to do it.

class gainView:

    def __init__(self, instrument: gain_inst.gainDevice):
        ui = Declarative.DeclarativeUI()

        self.init_pb = ui.create_push_button(text="Init", name="init_pb", on_clicked="init_push")

        self.start_label = ui.create_label(text='Start Wavelength (nm): ')
        self.start_line = ui.create_line_edit(text="@binding(instrument.start_wav_f)", name="start_line")
        self.pts_label = ui.create_label(text='E-points: ')
        self.pts_value_label = ui.create_label(text="@binding(instrument.pts_f)")
        self.ui_view1 = ui.create_row(self.start_label, self.start_line, ui.create_stretch(), self.pts_label,
                                      self.pts_value_label, spacing=12)

        self.finish_label = ui.create_label(text='Finish Wavelength (nm): ')
        self.finish_line = ui.create_line_edit(text="@binding(instrument.finish_wav_f)", name="finish_line")
        self.tpts_label = ui.create_label(text='Total points: ')
        self.tpts_value_label = ui.create_label(text='@binding(instrument.tpts_f)')
        self.ui_view2 = ui.create_row(self.finish_label, self.finish_line, ui.create_stretch(), self.tpts_label,
                                      self.tpts_value_label, spacing=12)

        self.step_label = ui.create_label(text='Step Wavelength (nm): ')
        self.step_line = ui.create_line_edit(text="@binding(instrument.step_wav_f)", name="step_line")
        self.current_label = ui.create_label(text='Current Wavelength (nm): ')
        self.current_value_label = ui.create_label(text='@binding(instrument.cur_wav_f)')
        self.ui_view3 = ui.create_row(self.step_label, self.step_line, ui.create_stretch(), self.current_label,
                                      self.current_value_label, spacing=12)

        self.avg_label = ui.create_label(text='Averages: ')
        self.avg_line = ui.create_line_edit(text="@binding(instrument.avg_f)", name="avg_line")
        self.running_label = ui.create_label(text='Is running? ')
        self.running_value_label = ui.create_label(text='@binding(instrument.run_status_f)')
        self.ui_view4 = ui.create_row(self.avg_label, self.avg_line, ui.create_stretch(), self.running_label,
                                      self.running_value_label, spacing=12)


        self.laser_group = ui.create_group(title='Sirah Credo', content=ui.create_column(
            self.ui_view1, self.ui_view2, self.ui_view3, self.ui_view4)
            )

        self.power_label = ui.create_label(text='Power (uW): ')
        self.power_value_label = ui.create_label(text="@binding(instrument.power_f)")
        self.power_lock_button = ui.create_push_button(text='Lock Current Power', name='Lock_power', on_clicked='lock_push')
        self.power_row00 = ui.create_row(self.power_label, self.power_value_label, ui.create_stretch(), self.power_lock_button)
        self.power_lock_label = ui.create_label(text='Control Power (uW): ')
        self.power_lock_value = ui.create_label(text='@binding(instrument.locked_power_f)')
        self.power_row01 = ui.create_row(self.power_lock_label, self.power_lock_value, ui.create_stretch())
        self.power_avg_label = ui.create_label(text='Number of Averages: ')
        self.power_avg_value = ui.create_line_edit(name='power_avg_value', text='@binding(instrument.powermeter_avg_f)')
        self.power_reset_button = ui.create_push_button(text='Hard Reset', name='power_reset_button', on_clicked='pw_hard_reset')
        self.power_row02 = ui.create_row(self.power_avg_label, self.power_avg_value, ui.create_stretch(), self.power_reset_button)

        self.powermeter_group = ui.create_group(title='ThorLabs PowerMeter', content=ui.create_column(
            self.power_row00, self.power_row01, self.power_row02)
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
        self.diode_cur_line = ui.create_line_edit(text='@binding(instrument.cur_d_edit_f)', name='cur_line')
        self.less_pb = ui.create_push_button(text="<<", name="less_pb", on_clicked="less_push", width=25)
        self.more_pb = ui.create_push_button(text=">>", name="more_pb", on_clicked="more_push", width=25)
        self.ui_view10 = ui.create_row(self.diode_cur_label, self.diode_cur_slider, self.text_label,
                                       self.diode_cur_line, ui.create_spacing(12), self.less_pb, ui.create_spacing(5),
                                       self.more_pb, ui.create_stretch())

        self.ps_group = ui.create_group(title='Laser PS', content=ui.create_column(
            self.ui_view8,
            self.ui_view9, self.ui_view10)
                                        )
        # Servo Motor

        self.servo_label = ui.create_label(text='Angle: ')
        self.servo_slider = ui.create_slider(name="servo_slider", value='@binding(instrument.servo_f)', minimum=0,
                                             maximum=180)
        self.less_servo_pb = ui.create_push_button(text="<<", name="less_servo_pb", on_clicked="less_servo_push",
                                                   width=25)
        self.more_servo_pb = ui.create_push_button(text=">>", name="more_servo_pb", on_clicked="more_servo_push",
                                                   width=25)
        self.servo_wobbler_cb = ui.create_check_box(text='Wobbler Servo', name='servo_wobbler_cb', checked='@binding(instrument.servo_wobbler_f)')

        self.servo_row = ui.create_row(self.servo_label, ui.create_spacing(12), self.servo_slider, ui.create_spacing(12), self.less_servo_pb, ui.create_spacing(5), self.more_servo_pb, ui.create_stretch(), self.servo_wobbler_cb)
    
        self.servo_step_label = ui.create_label(name='servo_step_label', text='Servo Step (°): ')
        self.servo_step_value = ui.create_line_edit(name='servo_step_value', text='@binding(instrument.servo_step_f)')
        self.servo_step_row = ui.create_row(self.servo_step_label, self.servo_step_value, ui.create_stretch())

        self.servo_group = ui.create_group(title='Servo Motor', content=ui.create_column(
            self.servo_row, self.servo_step_row))

        # Fast Blanker
        self.delay_label=ui.create_label(name='delay_label', text='Delay (ns): ')
        self.delay_value=ui.create_line_edit(name='delay_value', text='@binding(instrument.laser_delay_f)')
        self.delay_slider=ui.create_slider(name='delay_slider', value='@binding(instrument.laser_delay_f)', minimum=1740, maximum=1850)
        self.delay_row=ui.create_row(self.delay_label, self.delay_value, self.text_label, self.delay_slider, ui.create_stretch())

        self.width_label = ui.create_label(name='width_label', text='Width (ns): ')
        self.width_value = ui.create_line_edit(name='width_value', text='@binding(instrument.laser_width_f)')
        self.frequency_label = ui.create_label(name='frequency_label', text='Frequency (Hz): ')
        self.frequency_value = ui.create_line_edit(name='frequency_value', text='@binding(instrument.laser_frequency_f)')
        self.width_row=ui.create_row(self.width_label, self.width_value, ui.create_spacing(12),
                                     self.frequency_label, self.frequency_value, ui.create_stretch())

        self.stop_pb=ui.create_push_button(name='stop_pb', text='Stop All', on_clicked='stop_function')
        self.fast_blanker_checkbox = ui.create_check_box(name='fast_blanker_checkbox', checked='@binding(instrument.fast_blanker_status_f)', text='Shoot')
        self.counts_label = ui.create_label(name='counts_label', text='Counts: ')
        self.counts_value = ui.create_label(name='counts_value', text='@binding(instrument.laser_counts_f)')

        self.final_row=ui.create_row(self.fast_blanker_checkbox,
                                  ui.create_spacing(25), self.counts_label, self.counts_value, ui.create_spacing(25), self.stop_pb, ui.create_stretch())

        self.blanker_group=ui.create_group(title='Fast Blanker', content=ui.create_column(
            self.delay_row, self.width_row, self.final_row)
                                           )

        ## ACQUISTION BUTTONS
        
        self.upt_pb = ui.create_push_button(text="Update", name="upt_pb", on_clicked="upt_push")
        self.acq_pb = ui.create_push_button(text="Acquire", name="acq_pb", on_clicked="acq_push")
        self.abt_pb = ui.create_push_button(text="Abort", name="abt_pb", on_clicked="abt_push")
        self.buttons_row00 = ui.create_row(self.upt_pb, self.acq_pb, self.abt_pb, spacing=12)  

        self.power_ramp_pb = ui.create_push_button(text='Servo Scan', name='pr_pb', on_clicked="acq_pr_push")
        self.buttons_row01 = ui.create_row(self.power_ramp_pb, spacing=12)


        self.buttons_group=ui.create_group(title='Acquisition', content=ui.create_column(
            self.buttons_row00, self.buttons_row01))
        ## END FIRST TAB

        self.main_tab=ui.create_tab(label='Main', content=ui.create_column(
            self.init_pb, self.laser_group, self.powermeter_group, self.ps_group, self.servo_group, self.blanker_group, self.buttons_group))


        

        ### BEGIN MY SECOND TAB ##

        self.grab_pb = ui.create_push_button(text='Grab', name='grab_pb', on_clicked='grab_data_item')
        self.pb_row = ui.create_row(self.grab_pb, ui.create_stretch())

        self.file_name_label = ui.create_label(text='Title:', name='file_name_label')
        self.file_name_value = ui.create_line_edit(name = 'file_name_value')
        self.file_type_label = ui.create_label(text='Type: ', name='file_type_label')
        self.file_type_value = ui.create_label(text='type?', name='file_type_value')
        self.file_name_row = ui.create_row(self.file_name_label, self.file_name_value, ui.create_stretch(), self.file_type_label, self.file_type_value, ui.create_stretch())

        self.file_UUID_label = ui.create_label(text='UUID: ', name='file_UUID_label')
        self.file_UUID_value = ui.create_label(text='uuid?', name='file_UUID_value')
        self.file_dim_label = ui.create_label(text='Dim.: ', name='file_dim_label')
        self.file_dim_value = ui.create_label(text='dim?', name='file_dim_value')
        self.file_x_disp_label = ui.create_label(text='Dispersion: ', name='file_x_disp_label')
        self.file_x_disp_value = ui.create_label(text='disp?', name='file_x_disp_value')
        self.file_info_row = ui.create_row(self.file_UUID_label, self.file_UUID_value, self.file_dim_label, self.file_dim_value, self.file_x_disp_label, self.file_x_disp_value, spacing = 12)

        self.power_file_detected_label = ui.create_label(text='Power? ', name='power_file_detected_label')
        self.power_file_detected_value = ui.create_label(text='False', name='power_file_detected_value')
        self.wav_file_detected_label = ui.create_label(text='Wav? ', name='wav_file_detected_label')
        self.wav_file_detected_value = ui.create_label(text='False', name='wav_file_detected_value')
        self.detection_row = ui.create_row(self.power_file_detected_label, self.power_file_detected_value, ui.create_stretch(), self.wav_file_detected_label, self.wav_file_detected_value, ui.create_stretch())

        self.pts_detected_label = ui.create_label(text='Points: ', name='pts_detected_label')
        self.pts_detected_value = ui.create_label(text='pts?', name='pts_detected_value')
        self.avg_detected_label = ui.create_label(text='Averages: ', name='avg_detected_label')
        self.avg_detected_value = ui.create_label(text='avg?', name='avg_detected_value')
        self.start_detected_label = ui.create_label(text='Start Wav.: ', name='start_detected_label')
        self.start_detected_value = ui.create_label(text='st?', name = 'start_detected_value')
        self.final_detected_label = ui.create_label(text='End Wav.: ', name='final_detected_label')
        self.final_detected_value = ui.create_label(text='end?', name = 'final_detected_value')
        self.step_detected_label = ui.create_label(text='Step Wav.: ', name='step_detected_label')
        self.step_detected_value = ui.create_label(text='stp?', name='step_detected_value')

        self.first_detected_row = ui.create_row(self.pts_detected_label, self.pts_detected_value, self.avg_detected_label, self.avg_detected_value, spacing=12)
        self.second_detected_row = ui.create_row(self.start_detected_label, self.start_detected_value, self.final_detected_label, self.final_detected_value, self.step_detected_label, self.step_detected_value, spacing=12)


        self.pick_group = ui.create_group(title='Pick Tool', content=ui.create_column(
            self.file_name_row, self.file_info_row, self.detection_row, self.pb_row, self.first_detected_row, self.second_detected_row, ui.create_stretch()))

        self.align_zlp_max = ui.create_push_button(text='Align ZLP (Max)', on_clicked='align_zlp', name='align_zlp_max')
        self.align_zlp_fit = ui.create_push_button(text='Align ZLP (Fit)', on_clicked='align_zlp', name='align_zlp_fit')
        self.normalize_check_box = ui.create_check_box(text='Norm. by Power? ', name='normalize_check_box')
        self.normalize_current_check_box = ui.create_check_box(text='Norm. by Current? ', name='normalize_current_check_box')
        self.display_check_box = ui.create_check_box(text='Display?', name='display_check_box')
        self.pb_actions_row = ui.create_row(self.align_zlp_max, self.align_zlp_fit, self.normalize_check_box, self.normalize_current_check_box, self.display_check_box, spacing=12)
    
        self.zlp_label = ui.create_label(text='FWHM of ZLP: ', name='zlp_label')
        self.zlp_value = ui.create_label(text='fwhm?', name='zlp_value')
        self.zlp_row = ui.create_row(self.zlp_label, self.zlp_value, ui.create_stretch())

        self.savgol_window_label = ui.create_label(text='Smoothing Window: ', name='savgol_window_label')
        self.savgol_window_value = ui.create_line_edit(name='savgol_window_value')
        self.savgol_poly_order_label = ui.create_label(text='Poly Order: ', name='savgol_poly_order_label')
        self.savgol_poly_order_value = ui.create_line_edit(name='savgol_poly_order_value')
        self.savgol_oversample_label = ui.create_label(text='Oversampling: ', name='savgol_oversample_label')
        self.savgol_oversample_value = ui.create_line_edit(name='savgol_oversample_value')
        self.savgol_row = ui.create_row(self.savgol_window_label, self.savgol_window_value, self.savgol_poly_order_label, self.savgol_poly_order_value, self.savgol_oversample_label, self.savgol_oversample_value, ui.create_stretch())

        self.smooth_zlp = ui.create_push_button(text='Smooth ZLP', on_clicked='smooth_data', name='smooth_zlp')
        self.display_smooth_check_box = ui.create_check_box(text='Display?', name='display_smooth_check_box')
        self.smooth_row = ui.create_row(self.smooth_zlp, self.display_smooth_check_box, spacing=12)
        
        
        self.process_eegs_pb = ui.create_push_button(text='Process Laser Scan', on_clicked='process_data', name='process_eegs_pb')
        self.process_power_pb = ui.create_push_button(text='Process Power Scan', on_clicked='process_data', name='process_power_pb')
        self.pb_process_row = ui.create_row(self.process_eegs_pb, self.process_power_pb, spacing=12)


        self.actions_group = ui.create_group(title = 'Actions', content=ui.create_column(
            self.pb_actions_row, self.zlp_row, self.savgol_row, self.smooth_row, self.pb_process_row, ui.create_stretch())
            )

        self.ana_tab = ui.create_tab(label='Analysis', content=ui.create_column(
            self.pick_group, self.actions_group, ui.create_stretch())
            )




        self.tabs=ui.create_tabs(self.main_tab, self.ana_tab)




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
