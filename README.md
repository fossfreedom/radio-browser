Radio-Browser
=============

GTK3+ port from original source https://github.com/segler-alex/rhythmbox-radio-browser/issues
for Rhythmbox 2.96

Current situation as of:
29 Jul 2012 - GUI mostly ported. The third search tab is not functional as yet. 
It does play radio-stations from the default list and you can search for new radio stations

Help needed! 
============

known issues: 
-------------

1. radio station filter view does not display via icons and hangs on being filtered - currently no idea what the issue here is.
2. preferences button - functional but needs code cleanup (duplication of code and stop the need to restart rhythmbox before preferences are recognised)

Potential Enhancements
----------------------
1. In the radio_browser_source code there are some toolbar methods which are never called - could be useful to define the toolbar buttons

Ubuntu 12.04 notes:
-------------------

packages required to be installed:

   sudo apt-get install streamripper gir1.2-gconf-2.0


