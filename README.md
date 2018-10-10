The On Stage Lyrics Browser is an attempt to build a simple teleprompt
system for on-stage performances. 

The collection of scripts here, properly installed on a Raspberry Pi, 
will produce a simple, text-based browser for lyrics on a USB dongle.
 
## Included are:
 * a udev rule to auto mount/umount USB upon insertion/removal
 * a script that controls the interface display functions
 * a script that sends mount information to the interface
 * a script that sends umount information to the interface

## To install:
This assumes a recent copy of Raspian is installed and everything is
default.

#### Configure networking
This does not need to persist beyond installation. Be sure your Pi
can access APT repositories.
```sh
sudo ifconfig eth0 192.168.###.###
```

#### Install dependencies
```sh
apt install -y python3-rpi.gpio
```



## Credits
udev rules adapted from:\
https://www.axllent.org/docs/view/auto-mounting-usb-storage/

switch debounce circuit from:\
https://www.logiswitch.net/switch-debounce-diy_tutorial/method-4-hardware-debounce-for-spst-switches
