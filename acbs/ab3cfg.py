import os

from acbs import bashvar

class AB3Cfg(object):

    def __init__(self, path) -> None:
        '''
        Class representing autobuild3 config file.

        :param path: path to the ab3cfg.sh file, with the filename
        '''
        self.cfgpath = path
        self.file = None
        self.vars = None
        self.stage2 = False
        try:
            self.file = open(self.cfgpath, 'rt')
        except IOError:
            # You run ACBS then you should have AB3, eh?
            raise RuntimeError(f'Autobuild3 config file {self.cfgpath} does not exist\n' +
                               'Unable to read Autobuild3 config file.')
        if self.file:
            self.parse()

    def parse(self):
        '''
        Parse the ab3cfg.sh file.
        '''
        if self.file:
            try:
                self.vars = bashvar.eval_bashvar(self.file.read(), filename=self.cfgpath)
            except Exception as e:
                raise RuntimeError(f'Error parsing autobuild3 config file: {e}.')

    def is_in_stage2(self) -> bool:
        '''
        Return True if ab3 is in stage 2 mode.
        '''
        if self.vars:
            self.stage2 = ((self.vars.get('ABSTAGE2') == '1') or False)
        return self.stage2
