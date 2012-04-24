"""Helper funtions to read log files"""

from sys import maxint
from csv import reader

__author__ = "B. Henne"
__contact__ = "henne@dcsec.uni-hannover.de"
__copyright__ = "(c) 2011, DCSec, Leibniz Universitaet Hannover, Germany"
__license__ = "GPLv3"


def read_simple(filename, delimiter, t, x, y):
    """Reads complete CSV log file with time, x-value and y-value and return only this.
    @author: B. Henne"""
    logReader = reader(open(filename), delimiter=delimiter)
    for row in logReader:
        yield row[t], [row[x], row[y]]

def read(filename, delimiter, t, x, y, t_start=0, t_end=maxint, empty=[]):
    """Reads CSV log file with time, x-value and y-value for specified time interval. 
    Return values for all t_start < t < t_end.
    
    Times with no log entries are filled with value of empty. 
    Returns iterable pair of time and list of coordinates
    @param filename: name of csv file
    @param delimiter: delimiter between columns in csv file
    @param t: number of column containing time
    @param x: number of column containing x-value
    @param y: number of column containing y-value
    @param t_start: start of output time interval
    @param t_end: end of output time interval
    @param empty: value yielded if no log entry exists for a time, default is empty list, maybe use None
    @author: B. Henne"""
    logReader = reader(open(filename), delimiter=delimiter)
    t_now = t_start                 #: current iteration time
    row = logReader.next()          #: list of csv file as list of columns
    while t_now <= t_end:
        dxy = []
        dt = int(row[t])            #: read time
        dx = row[x]                 #: read x-value
        dy = row[y]                 #: read y-value
        if dt < t_start:             # read time before start: we do not want this values before start
            try:
                row = logReader.next()  # read next and start again
            except:
                pass
            continue
        if dt < t_now:              # read time before current iteration time
            yield t_now, empty
            t_now += 1
            continue
        if dt > t_now:              # read time is after current time
           yield t_now, empty        
           t_now += 1
           continue
        while t_now == dt:          # read time is current time
            dxy.append([dx, dy])
            try:
                row = logReader.next()
            except:
                dt = maxint
                break
            dt = int(row[t])
            dx = row[x]
            dy = row[y]
        yield t_now, dxy
        t_now += 1

def accumulated_read(filename, delimiter, t, x, y, t_start=0, t_end=maxint, step=10):
    """Reads CSV file as read(), but accumulates return values in step size packets.
    @author: B. Henne"""
    acc = []
    substep = 1
    for t, xy in read(filename, delimiter, t, x, y, t_start=t_start, t_end=t_end, empty=None):
        if xy is not None:
            acc.extend(xy)
        if substep % step == 0:
            yield t, acc
            acc = []
            last_acc = t
        substep += 1
    if last_acc != t:
        yield t, acc


if __name__ == '__main__':
    for t,xy in read('data/logfilereader_testdata.txt', ' ', 0, 1, 2, 0, 35):
        print t,xy
    for xy in accumulated_read('data/logfilereader_testdata.txt', ' ', 0, 1, 2, 10, 49, 10):
        print xy
