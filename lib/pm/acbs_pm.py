import logging
import subprocess
import os


class acbs_pm(object):

    def __init__(self):
        pm_mod_dir = os.path.dirname(os.path.realpath(__file__))
        pm_mod_files = os.listdir(pm_mod_dir)
        self.pm_backends = []
        for i in pm_mod_files:
            if i.endswith('.sh'):
                self.pm_backends.append(os.path.join(pm_mod_dir, i))
        logging.debug('Found pm_backends: {}'.format(self.pm_backends))
        return

    def query_current_miss_pkgs(self, pkgs):
        # self.multi_backend_proc('pm_repoupdate', '', True)
        miss_pkgs = []
        for pkg in pkgs:
            mixed_res = self.multi_backend_proc('pm_exists', pkg)
            for i in mixed_res:
                if mixed_res[i] is None:
                    miss_pkgs.append(pkg)
        miss_pkgs_set = set(miss_pkgs)
        return list(miss_pkgs_set)

    def query_online_pkgs(self, pkgs):
        not_online_pkgs = []
        for pkg in pkgs:
            mixed_res = self.multi_backend_proc('pm_repoquery', pkg)
            for i in mixed_res:
                if mixed_res[i] is None:
                    not_online_pkgs.append(pkg)
        online_pkgs_set = set(pkgs) - set(not_online_pkgs)
        return list(online_pkgs_set)

    def multi_backend_proc(self, function, args, display=False):
        hybrid_res = {}
        for bk in self.pm_backends:
            hybrid_res[os.path.basename(bk).split('.sh')[0]] = self.pm_invoker(
                bk, function, args, display)
        return hybrid_res

    def install_pkgs(self, pkgs):
        results = self.multi_backend_proc(
            'pm_repoinstall', ' '.join(pkgs), True)
        for result in results:
            if results[result] is None:
                return False
        return True

    def pm_invoker(self, mod_file, function, args, display=False):
        with open(mod_file, 'rt') as f:
            sh_code = f.read()
        excute_code = '%s\n%s %s\n' % (sh_code, function, args)
        try:
            if display:
                subprocess.check_call(excute_code, shell=True)
                return True
            else:
                output = subprocess.check_output(
                    excute_code, shell=True, stderr=subprocess.STDOUT)
            return output.decode('utf-8')
        except:
            return None
        return None
