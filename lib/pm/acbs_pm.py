from ..acbs_utils import acbs_utils
import logging


class acbs_pm(object):
    def __init__(self):
        self.known_pms = ['dpkg', 'rpm']  # ['dpkg', 'rpm', 'pacman']
        self.pms = []
        for pm in self.known_pms:
            acbs_utils.test_progs(pm)
            self.pms.append(pm)
# pms = ['dpkg', 'rpm']

    def query_current_miss_pkgs(self, pkgs):
        ret_dict = {}
        for pm in self.pms:
            code_obj = compile('miss_pkgs={}_miss_pkgs({})'.format(pm, pkgs), '<string>', 'exec')
            try:
                exec(code_obj)
            except NameError:
                logging.exception('An internal error occurred!')
                # Will be changed later
            except:
                logging.exception('An internal error occurred!')
            ret_dict[pm] = miss_pkgs
        return ret_dict

    def query_online_pkgs(self, pkgs):
        ret_dict = {}
        
