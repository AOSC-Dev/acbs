
class LoaderHelper(object):

    func_maps = {}

    def __init__(self):
        return

    @classmethod
    def register(cls, when, args=()):
        '''
        Register a callback

        :param when: When to call the callback
        :param args: Arguments that need to be passed to the callback, can't \
        be keyword arguments
        '''
        def func(fn):
            if not cls.func_maps.get(when):
                cls.func_maps[when] = [(fn, args)]
            else:
                cls.func_maps[when].append((fn, args))
            return fn
        return func

    @classmethod
    def clear(cls, when):
        '''
        Clear all callbacks in specified map

        :param when: Map to be cleared
        '''
        if cls.func_maps.get(when):
            cls.func_maps.pop(when)

    @staticmethod
    def callback(when, delete=True):
        cbs = LoaderHelper.func_maps.get(when)
        if cbs:
            for cb in cbs:
                cb[0](*cb[1])
        if delete:
            LoaderHelper.clear(when)
