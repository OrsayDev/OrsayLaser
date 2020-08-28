import numpy as np
import matplotlib.pyplot as plt

y = np.asarray([1371679, 1331113, 1310500, 1289668, 1268614, 1253744, 1247338, 1225840, 1193171])
x = np.asarray([540, 560, 570, 580, 590, 597, 600, 610, 625])

mode = "tri"

if (mode=="linear"):
    coefs = np.polynomial.polynomial.polyfit(x, y, 1)
    y_grat = coefs[1] * x + coefs[0]
if (mode=="quad"):
    coefs = np.polynomial.polynomial.polyfit(x, y, 2)
    y_grat = coefs[2] * x**2 + coefs[1] * x + coefs[0]
if (mode=="tri"):
    coefs = np.polynomial.polynomial.polyfit(x, y, 3)
    y_grat = coefs[3] * x**3 + coefs[2] * x**2 + coefs[1] * x + coefs[0]


print(coefs)


fig, ax = plt.subplots(2, 1, sharex=True, figsize=(9, 6), dpi=150)
ax[0].plot(x, y, label="Real Data")
ax[0].plot(x, y_grat, label = "Fitting Func")
ax[1].plot(x, y_grat-y, label = "Residue")
ax[0].legend()
ax[1].legend()
ax[0].set_ylabel("Position (A.U.)")
ax[1].set_ylabel("Position (A.U.)")
ax[1].set_xlabel("Wavelength (nm)")
plt.savefig("tri_fitting_pos.svg")
plt.show()

