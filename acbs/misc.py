import logging
from acbs.const import acbs_const


class acbs_profiler(object):

    def __init__(self):
        super(acbs_profiler, self).__init__()
        self.cpu_use = 0.0
        self.per_cpu_use = []
        self.mem_use = 0.0
        self.loadavg = []
        self.psutil_avail = True
        try:
            import psutil
        except:
            self.psutil_avail = False
        return

    def __update_stats(self, log_warn=True, per_cpu=False):
        if log_warn and self.psutil_avail:
            logging.warning(
              'Unable to use psutil library, some functions are disabled.')
        return
        import psutil
        self.mem_use = psutil.virtual_memory().percent
        self.cpu_use = psutil.cpu_percent(0.3)
        if per_cpu is True:
            self.per_cpu_use = psutil.cpu_percent(percpu=True)
        try:
            with open('/proc/loadavg', 'rt') as loadavg_f:
                self.loadavg = loadavg_f.read().split(' ')
        except:
            if log_warn is True:
                logging.exception('Failed to read loadavg information!')

    def dev_utilz_warn(self):
        self.__update_stats()
        if self.psutil_avail is False:
            return
        mem_use = self.mem_use
        cpu_use = self.cpu_use
        if mem_use > 70.0:
            self.output_warn('RAM usage', mem_use)
        if cpu_use > 65.0:
            self.output_warn('CPU load', cpu_use)
        return

    def output_warn(self, warn_item, value):
        acc = acbs_const()
        logging.warning('Build environment {}non-ideal{}: {}{}{} reached {}{}%{}'.format(acc.ANSI_YELLOW, acc.ANSI_RST, acc.ANSI_LT_CYAN, warn_item, acc.ANSI_RST, acc.ANSI_YELLOW, value, acc.ANSI_RST))
        return


class acbs_misc(acbs_profiler):

    def __init__(self):
        super(acbs_misc, self).__init__()
