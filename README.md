Export daily commits count from git repo history as daily calendar events.
Comits from all branches (including remote ones) are exported.

*Note: pip/easy_install/development_svn versions of iCalendar have buggy utf8 & long line support,
grab a fixed copy from [here](http://github.com/ryba-xek/iCalendar)*


### Basic usage (events get named by output filename):
    git2ical.py ./hub hub.ics
![Sample output in iCal](http://averin.ru/ext/github/git2ical/1.png)


### Events split by author:
    git2ical.py -a ../hub.git huba.ics
![Sample output in iCal by authors](http://averin.ru/ext/github/git2ical/2.png)

