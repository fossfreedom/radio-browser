DESTDIR=
SUBDIR=/usr/lib/rhythmbox/plugins/radio-browser/
DATADIR=/usr/share/rhythmbox/plugins/radio-browser/
LOCALEDIR=/usr/share/locale/

all:
clean:
	- rm *.pyc

install:
	install -d $(DESTDIR)$(SUBDIR)
	install -d $(DESTDIR)$(DATADIR)
	install -m 644 *.py $(DESTDIR)$(SUBDIR)
	install -m 644 *.png $(DESTDIR)$(DATADIR)
	install -m 644 *.ui $(DESTDIR)$(DATADIR)
	install -m 644 *.glade $(DESTDIR)$(DATADIR)
	install -m 644 radio-browser.plugin $(DESTDIR)$(SUBDIR)
