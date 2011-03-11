#!/usr/bin/env python
# -*- encoding: utf-8 -*-
#--- Author: Xek <s@averin.ru>
__version__ = '1.0b'

import re
from os.path import basename, exists, join
import hashlib
from datetime import date, datetime
from subprocess import Popen, PIPE
from icalendar import Calendar, Event, UTC
from optparse import OptionParser, OptionGroup, Option


STAR = u'☆'
STATSRE = re.compile(r'^(\d+) [^,]+, (\d+) [^,]+, (\d+) ')


def md5(str):
    return hashlib.md5(str).hexdigest()


#parse command line
def parse_cmdline():
    parser_opts = {
        'usage': 'usage: %prog [options] repo_folder ics_outfile',
        'description': 'Export daily commits count from git repo history \
            as daily calendar events',
        'version': __version__
    }
    parser = OptionParser(**parser_opts)
    parser.add_option("-a", "--split-authors", action="store_true", \
        dest="split_authors", default=False, help="split events by author")
    parser.add_option("-d", "--days", type='int', dest="last_days", \
        default=30, metavar='INT', help="output last INT days, 0=today, 1=today+yesterday, etc. (default 30)")
    (options, args) = parser.parse_args()
    if len(args) != 2:
        parser.print_usage()
        parser.exit(2)

    repo = args[0]
    outfile = args[1]
    if not exists(join(repo, 'config')) or not exists(join(repo, 'refs')):
        repo = join(repo, '.git')
        if not exists(join(repo, 'config')) or not exists(join(repo, 'refs')):
            parser.exit(2, 'Specified path does not seem like a git repo\n')

    return options.split_authors, options.last_days, repo, outfile


class Commit(object):
    def __init__(self, hash, ts, author, subject):
        self.hash = hash
        self.ts = ts
        self.author = author
        self.subject = subject

    def add_stats(self, files, lines_added, lines_deleted):
        self.files = files
        self.lines_added = lines_added
        self.lines_deleted = lines_deleted


def load_commits(repo, last_days):
    daydata = {}

    def add_commit(hash, ts, author, subject):
        c = Commit(hash, ts, author, subject)

        day = date.fromtimestamp(ts)
        if day not in daydata:
            daydata[day] = {}

        if author not in daydata[day]:
            daydata[day][author] = []

        daydata[day][author].append(c)

        return c

    #get git log
    git_params = [
        'git',
        '--git-dir=%s' % repo,
        'log',
        '--all',
        '--pretty=%h|%at|%an|%s',
        '--shortstat',
        '--since=-%d day 00:00' % last_days
    ]
    #print ' '.join(map(lambda c: c if not '=' in c else c[0:c.find('=')]+"='%s'"%c[c.find('=')+1:], git_params))
    p = Popen(git_params, stdout=PIPE)
    last_added_commit = None
    #try:
    for l in p.stdout:
        l = l.strip()
        if not l:
            continue

        if '|' in l:  # info: e7ed4df|1295817644|User|initial
            (hash, ts, author, subject) = l.split('|', 3)
            ts = int(ts)
            subject = subject.decode('utf8')
            last_added_commit = add_commit(hash, ts, author, subject)
        else:  # stats: 8 files changed, 205 insertions(+), 0 deletions(-)
            g = STATSRE.match(l)
            assert g is not None, last_added_commit is not None
            last_added_commit.add_stats(*g.groups())

    #finally:
    #	p.wait()

    return daydata


def make_cal(daydata, split_authors, repo_name, repo_hash):
    cal = Calendar()

    def add_event(summary, date, desc, uid):
        event = Event()
        event.add('summary', summary)
        event.add('dtstart', date)
        event.add('dtend', date)
        #event.add('dtstamp', date)
        #event.add('dtstart', datetime(date.year, \
        # date.month, date.day, 0, 10, 0, tzinfo=UTC))
        #event.add('dtend', datetime(date.year, \
        # date.month, date.day, 1, 10, 0, tzinfo=UTC))
        #event.add('dtstamp', datetime(date.year, \
        # date.month, date.day, 0, 10, 0, tzinfo=UTC))
        event.add('description', desc)
        event['uid'] = uid
        event.add('priority', 5)
        cal.add_component(event)

    cal.add('version', '2.0')
    cal.add('prodid', '-//git2ical//py//')

    if split_authors:
        for day in daydata:
            for author in daydata[day]:
                commits = daydata[day][author]
                summary = '%s: %d' % (author, len(commits))
                subjects = map(lambda c: u'— %s' % c.subject, commits)
                desc = u'\r\n'.join(subjects)
                uid = '%s_%s_%s@git2ical' % \
                      (md5(author)[0:8], md5(str(day))[0:8], repo_hash[0:8])
                add_event(summary, day, desc, uid)
    else:
        for day in daydata:
            summary = '%s: %d' % \
                      (repo_name, sum(map(len, daydata[day].itervalues())))
            subjects = []
            authors = daydata[day].keys()
            authors.sort()
            for author in authors:
                subjects.extend(['', '%s:' % author])
                commits = daydata[day][author]
                subjects.extend(map(lambda c: u'— %s' % c.subject, commits))
            desc = u'\r\n'.join(subjects)
            uid = '%s_%s@git2ical' % (md5(str(day))[0:8], repo_hash[0:8])
            add_event(summary, day, desc, uid)

    return cal


if __name__ == '__main__':
    split_authors, last_days, repo, outfile = parse_cmdline()
    repo_hash = md5(repo)
    repo_name = basename(outfile).rsplit('.', 1)[0]
    daydata = load_commits(repo, last_days)
    cal = make_cal(daydata, split_authors, repo_name, repo_hash)
    f = open(outfile, 'w')
    f.write(cal.as_string())
    f.close()
