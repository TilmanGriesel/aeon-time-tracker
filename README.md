A project that aims to be a NFC based hardware time tracker some day.

* Python
* SQLite
* Smartcard support

Currently focused for use with the Advanced Card Systems ACR122 NFC Reader / Writer

#### ACR122 Installation for debian-7.8.0-amd64
Get the ACR122 driver from http://www.acs.com.hk/download-driver-unified/5128/ACS-Unified-PKG-Lnx-110-P.zip
* ```sudo dpkg -i libacsccid1_1.1.0-1~trusty1_amd64.deb```
* ```sudo apt-get install libpcsclite1 pcscd pcsc-tools```
* ```sudo /etc/init.d/pcscd restart```
* ```sudo apt-get install python-pyscard```
* ```sudo apt-get install python-pip```
* ```sudo pip install dateutils```
* ```sudo apt-get install git```
* ```git clone https://github.com/TilmanGriesel/aeon-time-tracker.git```
* ```cp aeon_default.db aeon.db```
* ```python Playground.py```


#### Docs
http://www.acs.com.hk/download-manual/11/PPE-ACR122U-2.01.pdf

http://www.acs.com.hk/download-manual/418/TSP-ACR122U-3.03.pdf

http://www.acs.com.hk/download-manual/419/API-ACR122U-2.02.pdf
