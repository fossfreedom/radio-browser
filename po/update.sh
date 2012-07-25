#!/bin/sh
# update package.pot
echo "update package.pot"
intltool-update -p -g package

# update translations from webtranslateit
/var/lib/gems/1.8/bin/wti pull

# update radio-browser.rb-plugin
intltool-merge -d . ../radio-browser.rb-plugin.in ../radio-browser.rb-plugin
