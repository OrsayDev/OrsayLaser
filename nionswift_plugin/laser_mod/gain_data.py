import sys
import numpy
from scipy.signal import savgol_filter
from scipy.interpolate import interp1d
from scipy.optimize import curve_fit

__author__ = "Yves Auad"

class gainData:

    def __init__(self):
        pass

    def send_raw_MetaData(self, rd):
        index = [] #max position for alignment
        array = [0] * len(rd[0][0].data[0])
        temp_data =  [array] * len(rd)


        for i in range(len(rd)):
            for j in range(len(rd[i])):
                cam_hor = numpy.sum(rd[i][j].data, axis=0)
                index.append(numpy.where(cam_hor==numpy.max(cam_hor))[0][0]) #double [0] is because each numpy.where is a array of values. We dont want to have two maximums because aligning will be messy. Remember that we dont expect two maximuns in a ZLP that aren't pixels close together (probably neighbour)
                cam_hor = numpy.roll(cam_hor, -index[len(index)-1]+index[0])
                temp_data[i] = temp_data[i] + cam_hor

        temp_data = numpy.asarray(temp_data) #need this because nion gets some numpy array atributes, such as .shape
        return temp_data, index[0]

    def data_item_calibration(self, ic, dc, start_wav, step_wav, disp, index_zlp):
        ic.units='counts'
        dc[0].units='nm'
        dc[0].offset=start_wav
        dc[0].scale=step_wav
        dc[1].units='eV'
        dc[1].scale=disp
        dc[1].offset=-disp*index_zlp
        intensity_calibration = ic
        dimensional_calibrations = dc
        return intensity_calibration, dimensional_calibrations

    def send_info_data(self, info_data):
        temp_wl_data=[]
        temp_pw_data=[]
        temp_di_data=[]
        for i in range(len(info_data)):
            for j in range(len(info_data[i])):
                temp_wl_data.append(info_data[i][j][0])
                temp_pw_data.append(info_data[i][j][1])
                temp_di_data.append(info_data[i][j][2])
        temp_wl_data = numpy.asarray(temp_wl_data)
        temp_pw_data = numpy.asarray(temp_pw_data)
        temp_di_data = numpy.asarray(temp_di_data)
        return temp_wl_data, temp_pw_data, temp_di_data

    def fit_data(self, data, pts, start, end, step, disp, fwhm, orders):
        ene = 0
        def _gaussian_fit(x, *p):
            A, sigma, A_1, A_2, A_3, A_4, fond, x_off = p
            func = A * numpy.exp(-(x - x_off) ** 2 / (2. * sigma ** 2)) +\
                   A_1 * numpy.exp(-(x - ene - x_off) ** 2 / (2. * sigma ** 2)) +\
                   A_1 * numpy.exp(-(x + ene - x_off) ** 2 / (2. * sigma ** 2)) + fond
            if orders>1:
                func = func + A_2 * numpy.exp(-(x + 2.*ene - x_off) ** 2 / (2. * sigma ** 2)) +\
                   A_2 * numpy.exp(-(x - 2.*ene - x_off) ** 2 / (2. * sigma ** 2))
                if orders>2:
                    func = func + A_3 * numpy.exp(-(x + 3. * ene - x_off) ** 2 / (2. * sigma ** 2)) + \
                   A_3 * numpy.exp(-(x - 3. * ene - x_off) ** 2 / (2. * sigma ** 2))
                    if orders>3:
                        func = func + A_4 * numpy.exp(-(x + 4. * ene - x_off) ** 2 / (2. * sigma ** 2)) + \
                               A_4 * numpy.exp(-(x - 4. * ene - x_off) ** 2 / (2. * sigma ** 2))

            return func

        fit_array = numpy.zeros(data.shape)
        a_array = numpy.zeros(data.shape[0])
        a1_array = numpy.zeros(data.shape[0])
        a2_array = numpy.zeros(data.shape[0])
        a3_array = numpy.zeros(data.shape[0])
        a4_array = numpy.zeros(data.shape[0])
        sigma_array = numpy.zeros(data.shape[0])

        wavs = numpy.linspace(start, end, pts-1)
        energies_loss = numpy.divide(1239.8, wavs)
        energies_loss = numpy.append(energies_loss, 0.)

        for i in range(fit_array.shape[0]):
            x = numpy.linspace(-(fit_array.shape[1] / 2.) * disp, (fit_array.shape[1] / 2.) * disp, fit_array.shape[1])
            ene = energies_loss[i]
            p0 = [max(fit_array[i]), 1, 0., 0., 0., 0., data.min(), 0.]
            coeff, var_matrix = curve_fit(_gaussian_fit, x, data[i], p0=p0)
            a_array[i], a1_array[i], a2_array[i], a3_array[i], a4_array[i], sigma_array[i] = coeff[0], coeff[2], coeff[3], coeff[4], coeff[5], coeff[1]
            fit_array[i] = _gaussian_fit(x, *coeff)
            if ene: print(f'***ACQUISITION***: Fitting Data: ' + format(i/fit_array.shape[0]*100, '.0f') + '%. Current Wavelength is: ' + format(1239.8/ene, '.2f') + ' nm')
        return fit_array, a_array, a1_array, a2_array, a3_array, a4_array, sigma_array

    def align_zlp(self, raw_array, pts, avg, pixels, disp, mode='max'):

        def _gaussian(x, *p):
            A, mu, sigma = p
            return A*numpy.exp(-(x-mu)**2/(2.*sigma**2))

        def _gaussian_two_replicas(x, *p): #ONE GAIN ONE LOSS.
            A, mu, sigma, AG, muG, AL, muL = p
            return A*numpy.exp(-(x-mu)**2/(2.*sigma**2)) + AG*numpy.exp(-(x-muG)**2/(2.*sigma**2)) + AL*numpy.exp(-(x-muL)**2/(2.*sigma**2))
        
        proc_array = numpy.zeros((pts, pixels))
        zlp_fit = numpy.zeros(avg)

        if 'max' in mode:
            for i in range(len(proc_array)):
                for j in range(avg):
                    current_max_index = numpy.where(raw_array[i*avg+j]==numpy.max(raw_array[i*avg+j]))[0][0]
                    proc_array[i] = proc_array[i] + numpy.roll(raw_array[i*avg+j], -current_max_index + int(pixels/2))
                    x = numpy.linspace((-pixels/2.+1)*disp, (pixels/2.)*disp, pixels)
                    p0 = [max(proc_array[i]), 0., 1]
                    coeff, var_matrix = curve_fit(_gaussian, x, proc_array[i], p0 = p0)
                    if i==(len(proc_array)-1):
                        zlp_fit[j] = coeff[2]
            return proc_array, 2*numpy.mean(zlp_fit)*numpy.sqrt(2.*numpy.log(2))

        if 'fit' in mode: #I HAVE SUB PIXEL WITH MAX_INDEX. How to improve further with fit? I am not sure.
            for i in range(len(proc_array)):
                for j in range(avg):
                    current_max_index = numpy.where(raw_array[i*avg+j]==numpy.max(raw_array[i*avg+j]))[0][0]
                    proc_array[i] = proc_array[i] + numpy.roll(raw_array[i*avg+j], -current_max_index + int(pixels/2))
                    x = numpy.linspace((-pixels/2.+1)*disp, (pixels/2.)*disp, pixels)
                    p0 = [max(proc_array[i]), 0., 1]
                    coeff, var_matrix = curve_fit(_gaussian, x, proc_array[i], p0=p0)
                    if i==(len(proc_array)-1):
                        zlp_fit[j] = coeff[2]
            return proc_array, 2*numpy.mean(zlp_fit)*numpy.sqrt(2.*numpy.log(2))

        if 'f_plot' in mode:
            for i in range(len(proc_array)):
                for j in range(avg):
                    current_max_index = numpy.where(raw_array[i*avg+j]==numpy.max(raw_array[i*avg+j]))[0][0]
                    proc_array[i] = proc_array[i] + numpy.roll(raw_array[i*avg+j], -current_max_index + int(pixels/2))
                    x = numpy.linspace((-pixels/2.+1)*disp, (pixels/2.)*disp, pixels)
                    p0 = [max(proc_array[i]), 0., 1., 0., -2., 0., 2.]
                    coeff, var_matrix = curve_fit(_gaussian_two_replicas, x, proc_array[i], p0 = p0)
                    proc_array[i] = _gaussian_two_replicas(x, *coeff)
            return proc_array, None


    def smooth_zlp(self, raw_array, window_size, poly_order, oversample, x, xx):
        smooth_array = numpy.zeros((raw_array.shape[0], raw_array.shape[1]*oversample))
        for i in range(len(raw_array)):
            itp = interp1d(x, raw_array[i], 'linear')
            smooth_array[i] = savgol_filter(itp(xx), window_size, poly_order)
        return smooth_array

    def as_power_func(self, raw_array, power_array):
        f = interp1d(power_array, raw_array, 'linear')
        power_array_new = numpy.linspace(power_array.min(), power_array.max(), len(power_array))
        raw_array_new = f(power_array_new)
        #the subtraction i am returning is to known the power increment
        return power_array_new, raw_array_new, power_array_new[1]-power_array_new[0]
