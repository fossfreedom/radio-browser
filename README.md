Radio-Browser
=============

GTK3+ port from original source https://github.com/segler-alex/rhythmbox-radio-browser/issues
for Rhythmbox 2.96

Current situation as of:
21 Aug 2012 - GUI ported. The third search tab is functional but a little buggy. 
It does play radio-stations from the default list and you can search for new radio stations

Help needed! 
============

known issues: 
-------------

1. radio station filter view is very slow when filtering.
2. preferences button - functional but needs code cleanup (duplication of code and stop the need to restart rhythmbox before preferences are recognised)
3. the station filter always seems to retrieve a new list on startup hence appears very slow - probably should really cache until the user actually says to download new stations.


Ubuntu 12.04 notes:
-------------------

packages required to be installed:

   sudo apt-get install streamripper gir1.2-gconf-2.0


