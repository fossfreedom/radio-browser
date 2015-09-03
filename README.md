Radio-Browser
=============

GTK3+ port from original source https://github.com/segler-alex/rhythmbox-radio-browser/issues
for Rhythmbox 3.0 and later

##GTK3 Author

 - fossfreedom <foss.freedom@gmail.com>, website - https://github.com/fossfreedom

[![Flattr Button](http://api.flattr.com/button/button-compact-static-100x17.png "Flattr This!")](https://flattr.com/thing/1237090/fossfreedomradio-browser-on-GitHub "fossfreedom")  [![paypaldonate](https://www.paypalobjects.com/en_GB/i/btn/btn_donate_SM.gif)](https://www.paypal.com/cgi-bin/webscr?cmd=_s-xclick&hosted_button_id=KBV682WJ3BDGL)

--


 - http://askubuntu.com/questions/210688/how-to-integrate-rhythmbox-to-play-internet-radio/210726#210726

![pic](http://i.stack.imgur.com/txTPz.png)

Installation
------------

<pre>
git clone https://github.com/fossfreedom/radio-browser -b rb3
cd radio-browser
./install.sh
</pre>

For a system wide install then:

<pre>
git clone https://github.com/fossfreedom/radio-browser -b rb3
cd radio-browser
sudo make install
</pre>

Then launch rhythmbox and enable the plugin "Internet Radio Browser"

Non-Debian based distros
------------------------

You will need to install the equivalent packages for your distro: `streamripper`

Debian & Ubuntu 14.04 notes:
-------------------

packages required to be installed:

    sudo apt-get install streamripper
