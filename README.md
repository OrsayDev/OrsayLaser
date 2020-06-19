# Laser Module
Module for controlling Laser in nionswift environment

# Installing
Clone master branch or most up-to-date development branch using:

`git clone https://github.com/yvesauad/yvorsay-instrument.git`

Inside your nionswift environment, if you are using anaconda/conda, install locally using 

`pip install -e yvorsay-intrument`

All required packages will be automatically installed. In this case, we use pyvisa (+pyusb +pyvisa-py) for controlling thorlabs PMUSB100 powermeter and pyserial for controlling Spectra Physics laser power supply and laser wavelength grating

# Troubleshoot

Inside our instrument file [gain_inst.py] there is a DEBUG variable for all three instruments, in which the value 1 means they will be run in a virtual instrument. All instruments have a hardware controlled file and a virtual one. If you obtain Serial errors during an attempt of opening Nionswift, please put everything in DEBUG mode and run again. Afterwards, check each hardware individually using our hello_hardware folders for each one of them. All examples are safe, but please read carefully what you doing before attempting.

In case of persistence of errors, check if all libraries were properly installed using

`pip list` or `conda list`

# Known Issues

If you using linux, check permission in your USB ports. To see if you instrument is detect, run list_resources using pyvisa, for instance. Thorlabs power meter doesn't show up until you modify your `/etc/udev/rules.d`. A workaround to list resources in our hello_hardware example is simply running python as super user.

If you are using windows, thorlabs powermeter also can cause issues, specially if you have multiply powermeters using in the same machine. Install official powermeter driver from thorlabs and use the executable Power Meter Driver Switcher to properly select the desired powermeter.
