Radio-Browser
=============

GTK3+ port from original source https://github.com/segler-alex/rhythmbox-radio-browser/issues
for Rhythmbox 2.96

Current situation as of:
26 Jul 2012 - not fully working port as yet. GUI mostly ported. 

It does play radio-stations from the default list and you can search for new radio stations

Help needed! 
============

known issues: 
-------------

1. preferences button do not read nor write values from/to gconf
2. need static constants for preferences objects
3. copyright info needs to state "derivative software" remark with originating source of "alex segler"


Ubuntu 12.04 notes:
-------------------

packages required to be installed:

   sudo apt-get install streamripper gir1.2-gconf-2.0

Future enhancements to be considered:
-------------------------------------

look to obtaining radio information from radio.de group of websites as per unity-lens-radios
