# standard libraries
import gettext
import logging
import threading
import time

# third party libraries
import numpy as np

# local libraries
from nion.data import xdata_1_0 as xd
from nion.swift.model import Utility
from nion.swift.model import HardwareSource as HardwareSourceModule
from nion.utils import Model
import nionlib


_ = gettext.gettext


class PanelExampleDelegate(object):

    def __init__(self, api):
        logging.info("init")
        self.panel_id = "gain-panel_v2"
        self.panel_name = "Gain Scanning v_2.0"
        self.panel_positions = ["left", "right"]
        self.panel_position = "left"
        self.__thread = None
        
        self.start_wav=550
        self.finish_wav=650
        self.step_wav=0.1
        self.avg=1
        self.dwell=1
        self.now_wav=self.start_wav
        self.status=False
        self.stored=False
        self.pts=int((self.finish_wav-self.start_wav)/self.step_wav+1)
        self.t_pts=int(self.pts*self.avg)

        self.demo_eres = 2.0 #eV
        self.demo_sig = 0.1 #eV
        self.demo_gun = 0.3 #eV

    
    def create_panel_widget(self, ui, document_controller):

        def upt_button_clicked():
            if (self.stored==False and self.status==False):
                self.start_wav = float(start_line.text)
                self.finish_wav = float(finish_line.text)
                self.step_wav = float(step_line.text)
                self.pts = int((float(finish_line.text)-float(start_line.text))/float(step_line.text)+1)
                self.t_pts=int(self.pts*float(avg_line.text))
                self.avg=int(float(avg_line.text))
                self.dwell=int(float(dwell_line.text))
            else:
                logging.info("There is data stored or thread is running. Please Acquire data if nothing is running...")

            label_pts.text = self.pts
            label_t_pts.text = self.t_pts
            label_cur.text = int(self.now_wav)
            label_running.text = str(self.status)
            label_stored.text = str(self.stored)

            
            #setting camera
            frame_parameters["integration_count"]=int(self.avg)
            frame_parameters["exposure_ms"]=int(self.dwell)
            frame_parameters["binning"]=1
            camera.set_current_frame_parameters(frame_parameters)

            
        def editing_finished(text):
            upt_button_clicked()
            

        def acq_button_clicked():
            upt_button_clicked()
            if (self.stored==False and self.status==False and demo_box.checked==False):
                self.__thread = threading.Thread(target=acq)
                self.__thread.start()
            if (demo_box.checked==True):
                logging.info("Let's not acquire new data is demo mode is ON. You can try the button Generate in order to have a right-on gain simulation given by demo parameters.")
            
        def gen_button_clicked():
            if (demo_box.checked):
                logging.info("Demo plotting...")
                data_complet = np.random.randn(self.pts, 1024)
                for i in range(self.pts):
                    data_complet[i]=plot_gaussian_gain(0, float(demo_gun_line.text), self.start_wav+i*self.step_wav, float(demo_eres_line.text), float(demo_sig_line.text))
                document_controller.create_data_item_from_data(data_complet, str(self.start_wav)+"-"+str(self.finish_wav)+"-"+str(self.step_wav)+"demo-"+str(demo_eres_line.text)+"-"+str(demo_sig_line.text)+"-"+str(demo_gun_line.text))
                logging.info("Finished demo plotting...")





            if (self.stored == True and demo_box.checked==False):
                logging.info("Plotting...")
                pixels = (len(self.data[0].data[0]))
                self.len = pixels
                data_complet = np.random.randn(self.pts, pixels)
                
                for i in range(len(self.data)):
                    temp_data=np.sum(self.data[i].data, axis=0)
                    #if (demo_box.checked):
                     #   data_complet[i]=plot_gaussian_gain(0, float(demo_gun_line.text), self.start_wav+i*self.step_wav, float(demo_eres_line.text), float(demo_sig_line.text))
                    #else:
                    data_complet[i] = temp_data
                        
                #if (demo_box.checked):
                 #   document_controller.create_data_item_from_data(data_complet, str(self.start_wav)+"-"+str(self.finish_wav)+"-"+str(self.step_wav)+"demo-"+str(demo_eres_line.text)+"-"+str(demo_sig_line.text)+"-"+str(demo_gun_line.text))
                #else:
                document_controller.create_data_item_from_data(data_complet, str(self.start_wav)+"-"+str(self.finish_wav)+"-"+str(self.step_wav))


                self.stored=False ##STORED DATA IS FALSE
            if (self.stored == False and demo_box.checked==False):
                logging.info("Nothing to Plot boys")

        def plot_gaussian_gain(cen, sig, wav, e_res, sig_res):
            g_energy = 1240./wav
            xx=np.linspace(-10, 10, 1024)
            
            amp = 1.0*np.e**((-(g_energy-e_res)**2) / (2*(sig_res)**2) ) + 1.0*np.e**((-(g_energy+e_res)**2) / (2*(sig_res)**2) )
            
            gau_datax=np.e**((-(xx-cen)**2) / (2*sig**2) ) + amp*np.e**((-(xx-cen-g_energy)**2) / (2*sig**2) ) + amp*np.e**((-(xx-cen+g_energy)**2) / (2*sig**2) )
            return gau_datax
            
        
        def acq():
            
            self.status=True
            data_metadata=[]
            for i in range(int(self.pts)):
                self.now_wav=self.start_wav+i*self.step_wav
                print(self.now_wav)
                data_metadata.append([])
                data_metadata[i]=camera.grab_next_to_start()[0]

            self.data=data_metadata
            logging.info("Acquisition Finished")
            self.stored=True ##STORED DATA IS TRUE
            self.status=False
            camera.stop_playing()

        
        #############################################################
        #logging.info("test0")
        #############################################################
        camera=HardwareSourceModule.HardwareSourceManager().hardware_sources[0]
        frame_parameters = camera.get_current_frame_parameters()

        column = ui.create_column_widget()

        edit_row = ui.create_row_widget()
        edit_row.add(ui.create_label_widget(_("Start Wavelength (nm): ")))
        edit_row.add_spacing(12)
        start_line = ui.create_line_edit_widget(self.start_wav)
        start_line.on_editing_finished = editing_finished
        edit_row.add(start_line)

        edit_row.add_spacing(12)
        edit_row.add(ui.create_label_widget(_("E-points: ")))
        edit_row.add_spacing(12)
        label_pts=ui.create_label_widget(self.pts)
        edit_row.add(label_pts)
        edit_row.add_stretch()

        #############################################################
        #logging.info("test1")
        #############################################################

        edit_row2 = ui.create_row_widget()
        edit_row2.add(ui.create_label_widget(_("Finish Wavelength (nm): ")))
        edit_row2.add_spacing(12)
        finish_line = ui.create_line_edit_widget(self.finish_wav)
        finish_line.on_editing_finished = editing_finished
        edit_row2.add(finish_line)
        
        edit_row2.add_spacing(12)
        edit_row2.add(ui.create_label_widget(_("Total Spectra: ")))
        edit_row2.add_spacing(12)
        label_t_pts=ui.create_label_widget(self.t_pts)
        edit_row2.add(label_t_pts)
        edit_row2.add_stretch()

        #############################################################
        #logging.info("test2")
        #############################################################
        
        edit_row3 = ui.create_row_widget()
        edit_row3.add(ui.create_label_widget(_("Wavelength step (nm): ")))
        edit_row3.add_spacing(12)
        step_line = ui.create_line_edit_widget(self.step_wav)
        step_line.on_editing_finished = editing_finished
        edit_row3.add(step_line)
        edit_row3.add_stretch()
        
        edit_row3.add(ui.create_label_widget(("Current Wavelength (nm): ")))
        edit_row3.add_spacing(12)
        label_cur=ui.create_label_widget(self.start_wav)
        edit_row3.add(label_cur)
        edit_row3.add_stretch()
        
        #############################################################
        #logging.info("test3")
        #############################################################
        
        edit_row4 = ui.create_row_widget()
        edit_row4.add(ui.create_label_widget(_("# Averages: ")))
        edit_row4.add_spacing(12)
        avg_line = ui.create_line_edit_widget(self.avg)
        avg_line.on_editing_finished = editing_finished
        edit_row4.add(avg_line)
        edit_row4.add_stretch()
        
        edit_row4.add_spacing(12)
        edit_row4.add(ui.create_label_widget(_("Is Running? ")))
        edit_row4.add_spacing(12)
        label_running=ui.create_label_widget(str(self.status))
        edit_row4.add(label_running)
        edit_row4.add_stretch()
        
        #############################################################
        #logging.info("test4")
        #############################################################
        
        edit_row5 = ui.create_row_widget()
        edit_row5.add(ui.create_label_widget(_("Dwell Time (ms): ")))
        edit_row5.add_spacing(12)
        dwell_line = ui.create_line_edit_widget(self.dwell)
        dwell_line.on_editing_finished = editing_finished
        edit_row5.add(dwell_line)
        edit_row5.add_stretch()
        
        edit_row5.add(ui.create_label_widget(("Stored Data? ")))
        edit_row5.add_spacing(12)
        label_stored=ui.create_label_widget(str(self.stored))
        edit_row5.add(label_stored)
        edit_row5.add_stretch()
        

        #############################################################
        #logging.info("test5")
        #############################################################
        
        button_row = ui.create_row_widget()
        button_widget = ui.create_push_button_widget(_("Update"))
        acq_button = ui.create_push_button_widget("Acquire")
        gen_button = ui.create_push_button_widget("Generate")
        cam_choice_drop = ui.create_combo_box_widget([HardwareSourceModule.HardwareSourceManager().hardware_sources[0].hardware_source_id, "?"])
        button_widget.on_clicked = upt_button_clicked
        acq_button.on_clicked = acq_button_clicked
        gen_button.on_clicked = gen_button_clicked
        button_row.add(button_widget)
        button_row.add_spacing(12)
        button_row.add(acq_button)
        button_row.add_spacing(12)
        button_row.add(gen_button)
        button_row.add_spacing(12)
        button_row.add(cam_choice_drop)
        button_row.add_stretch()
        
        #############################################################
        #logging.info("test6")
        #############################################################

        demo_row = ui.create_row_widget()
        demo_box = ui.create_check_box_widget("Demo Mode ")
        demo_box.checked=True
        
        demo_eres_line = ui.create_line_edit_widget(self.demo_eres)
        demo_eres_line.on_editing_finished = editing_finished
        demo_sig_line = ui.create_line_edit_widget(self.demo_sig)
        demo_sig_line.on_editing_finished = editing_finished
        demo_gun_line = ui.create_line_edit_widget(self.demo_gun)
        demo_gun_line.on_editing_finished = editing_finished
        
        
        demo_row.add(demo_box)
        demo_row.add_spacing(12)
        demo_row.add(ui.create_label_widget(_("E-Res (eV): ")))
        demo_row.add_spacing(12)
        demo_row.add(demo_eres_line)
        demo_row.add_spacing(12)
        demo_row.add(ui.create_label_widget(_("Sigma-Res (eV): ")))
        demo_row.add_spacing(12)
        demo_row.add(demo_sig_line)
        demo_row.add_spacing(12)
        demo_row.add(ui.create_label_widget(_("Gun FWHM (eV): ")))
        demo_row.add_spacing(12)
        demo_row.add(demo_gun_line)

        #############################################################
        #logging.info("test7")
        #############################################################

        column.add_spacing(8)
        column.add(edit_row)
        column.add(edit_row2)
        column.add(edit_row3)
        column.add(edit_row4)
        column.add(edit_row5)
        column.add(button_row)
        column.add(demo_row)
        column.add_spacing(8)
        column.add_stretch()

        return column


class PanelExampleExtension(object):

    # required for Swift to recognize this as an extension class.
    extension_id = "nion.swift.examples.panel_example_v2"

    def __init__(self, api_broker):
        # grab the api object.
        api = api_broker.get_api(version="1", ui_version="1")
        
        # grab camera, but this is not working
        camera = api.get_hardware_source_by_id("usim_eels_camera", "1")
        
        # be sure to keep a reference or it will be closed immediately.
        self.__panel_ref = api.create_panel(PanelExampleDelegate(api))


    def close(self):
        # close will be called when the extension is unloaded. in turn, close any references so they get closed. this
        # is not strictly necessary since the references will be deleted naturally when this object is deleted.
        self.__panel_ref.close()
        self.__panel_ref = None
