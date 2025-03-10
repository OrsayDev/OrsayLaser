from nion.instrumentation import HardwareSource
from nion.utils import Registry
from nion.typeshed import API_1_0 as API
from nion.typeshed import UI_1_0 as UI
from nion.typeshed import Interactive_1_0 as Interactive

import time, numpy

api = api_broker.get_api(API.version, UI.version)  # type: API
POINTS = 50


def script_main(api_broker):
    interactive: Interactive.Interactive = api_broker.get_interactive(Interactive.version)
    api = api_broker.get_api(API.version, UI.version)  # type: API
    window = api.application.document_windows[0]

    #Getting the reference of necessary objects
    cathodo_camera = HardwareSource.HardwareSourceManager().get_hardware_source_for_hardware_source_id(
        "orsay_camera_eire")
    main_controller = Registry.get_component("stem_controller")

    ### Getting the laser
    nkt_laser = Registry.get_component("sgain_controller_nkt")
    nkt_laser.emission_f = False

    ### Getting the min and the max wavelength
    min_wv = interactive.get_float("Minimum wavelength (nm): ")
    max_wv = interactive.get_float("Maximum wavelength (nm): ")
    nb_wv = interactive.get_integer("Number of spectra: ")
    step_wv = (max_wv - min_wv) / nb_wv

    #Displaying the data item. It will be updated line by line in the control loop
    dimensional_calibration_0 = api.create_calibration(min_wv, step_wv, 'nm')
    dimensional_calibration_1 = api.create_calibration(0, 100 // POINTS, 'Power (%)')
    dimensional_calibration = [dimensional_calibration_0, dimensional_calibration_1]

    data = numpy.zeros((nb_wv, POINTS))
    xdata = api.create_data_and_metadata(data, dimensional_calibrations=dimensional_calibration)
    data_item = api.library.create_data_item_from_data_and_metadata(xdata)
    data_item.title = "LaserCalibration"
    _display_panel = window.display_data_item(data_item)

    ### Doing the procedure
    wv_list = numpy.linspace(min_wv, max_wv, nb_wv)
    power_list = numpy.linspace(0, 100, POINTS)

    nkt_laser.emission_f = True
    should_break = False
    for wl_index, wl in enumerate(wv_list):
        print(f'Progress: {wl_index * 100 // nb_wv}%.')
        for laser_index, laser_power in enumerate(power_list):
            if should_break: break
            should_break = interactive.cancelled
            #nkt_laser.laser_intensity_f = laser_power #The supply
            nkt_laser.amp0_f = laser_power #The RF amplitude
            nkt_laser.start_wav_f = wl
            time.sleep(0.01)
            powermeter_value = nkt_laser.power_f
            data[wl_index, laser_index] = powermeter_value
        data_item.set_data_and_metadata(xdata)













# timepix3.start_playing()
# #scan.start_playing()
# #print(dir(scan.scan_device))
# print(main_controller.scan_controller.scan_device.scan_device_id)
# print(scan.scan_device.probe_pos)
# print(main_controller.probe_state)
# scan.scan_device.probe_pos = (0.5, 0.5)
# main_controller.probe_pos = (0.5, 0.5)
# print(scan.scan_device.probe_pos)
# print(main_controller.probe_position)
# time.sleep(0.5)
# timepix3.stop_playing()

