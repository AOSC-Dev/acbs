import logging
import subprocess
import os
from shlex import quote


class PackageManager(object):

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
                if mixed_res[i] is False:
                    miss_pkgs.append(pkg)
        miss_pkgs_set = set(miss_pkgs)
        return list(miss_pkgs_set)

    def query_online_pkgs(self, pkgs):
        not_online_pkgs = []
        for pkg in pkgs:
            mixed_res = self.multi_backend_proc('pm_repoquery', pkg)
            for i in mixed_res:
                if mixed_res[i] is False:
                    not_online_pkgs.append(pkg)
        online_pkgs_set = set(pkgs) - set(not_online_pkgs)
        return list(online_pkgs_set)

    def multi_backend_proc(self, function, args, display=False):
        """args: shell eval-style arguments. USE shlex.quote() or else."""
        hybrid_res = {}
        for bk in self.pm_backends:
            bk_name = os.path.basename(bk).split('.sh')[0]
            bk_res = self.pm_invoker(bk, function, args, display)
            hybrid_res[bk_name] = bk_res
            logging.debug('PM Backend: %s CMD: %s(%r) Res: %s' %
                          (bk_name, function, args, bk_res))
        return hybrid_res

    def correct_deps(self):
        results = self.multi_backend_proc('pm_correction', '', True)
        for result in results:
            if not results[result]:
                raise Exception('Failed to correct dependencies, you need to do this manually')
        return

    def install_pkgs(self, pkgs):
        results = self.multi_backend_proc(
            'pm_repoinstall', ' '.join(map(quote, pkgs)), True)
        for result in results:
            if not results[result]:
                raise subprocess.SubprocessError('Failed to install packages')
        return

    def pm_invoker(self, mod_file, function, args, display=False):
        """args: shell eval-style arguments. USE shlex.quote() or else."""
        with open(mod_file, 'rt') as f:
            sh_code = f.read()
        excute_code = ('%s\n%s %s\n' % (sh_code, function, args)).encode()
        try:
            if display:
                try:
                    subprocess.run(['bash'], input=excute_code, check=True)
                    return True
                except subprocess.CalledProcessError:
                    return False
            try:
                output = subprocess.run(
                    ['bash'], input=excute_code, stderr=subprocess.STDOUT,
                    stdout=subprocess.PIPE, check=True)
                return output.decode('utf-8')
            except subprocess.CalledProcessError:
                return False
        except Exception:
            return
        return
