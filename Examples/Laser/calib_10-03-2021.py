import numpy as np
from scipy.optimize import curve_fit
import matplotlib.pyplot as plt

x = np.asarray([1371679, 1361620, 1351505, 1341337, 1331113, 1320834, 1310500, 1300111, 1289668, 1279168, 1268614, 1258004, 1247338, 1236617, 1225840, 1215007, 1204117, 1193171, 1182168, 1171108, 1159991, 1148816, 1137584, 1126293, 1114944, 1103537, 1092070, 1068957, 1045602, 1022003, 998154, 974052, 949691, 925067, 900174], dtype=np.float)
y = np.asarray([540, 545, 550, 555, 560, 565, 570, 575, 580, 585, 590, 595, 600, 605, 610, 615, 620, 625, 630, 635, 640, 645, 650, 655, 660, 665, 670, 680, 690, 700, 710, 720, 730, 740, 750], dtype=np.float)
y = np.add(y, 0.9)

def func(x, a, b, c, d, e, f):
    return a*x**5 + b*x**4 + c*x**3 + d*x**2 + e*x**1 + f*x**0

popt, pcov = curve_fit(func, x, y, method='lm')

print(popt)


fig, ax = plt.subplots(2, 1, sharex=True, figsize=(9, 6), dpi=150)
ax[0].scatter(x, y)
ax[0].plot(x, y, label="Real Data")
ax[0].plot(x, func(x, *popt), label = "Fitting Func")
ax[1].plot(x, func(x, *popt)-y, label = "Residue")
ax[0].legend()
ax[1].legend()
ax[0].set_xlabel("Position (A.U.)")
ax[0].set_ylabel("Wavelength (nm)")
ax[1].set_ylabel("Wavelength (nm)")
plt.savefig("tri_fitting_pos.svg")
plt.show()

