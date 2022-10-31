import os

from acbs import bashvar

class AB3Cfg(object):

    def __init__(self, path) -> None:
        '''
        Class representing autobuild3 config file.

        :param path: path to the ab3cfg.sh file, with the filename
        '''
        self.cfgpath = path
        self.vars = None
        self.stage2 = False
        try:
            with open(self.cfgpath, 'rt') as cfgfile:
                self.parse(cfgfile)
        except Exception as e:
            # You run ACBS then you should have AB3, eh?
            raise RuntimeError(f'Autobuild3 config file {self.cfgpath} does not exist\n' +
                               'Unable to read Autobuild3 config file.') from e

    def parse(self, file):
        '''
        Parse the ab3cfg.sh file.
        '''
        try:
            self.vars = bashvar.eval_bashvar(file.read(), filename=self.cfgpath)
        except Exception as e:
            raise RuntimeError(f'Error parsing autobuild3 config file: {e}.') from e

    def is_in_stage2(self) -> bool:
        '''
        Return True if ab3 is in stage 2 mode.
        '''
        if self.vars:
            self.stage2 = ((self.vars.get('ABSTAGE2') == '1') or False)
        return self.stage2
