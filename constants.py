def constant(f):
    def fset(self, value):
        raise TypeError
    def fget(self):
        return f()
    return property(fget, fset)

class _Const(object):
    @constant
    def VERSION():
        return "3.0"
    @constant
    def USER_AGENT():
        return "Rhythmbox Radio Browser 3.0"
    @constant
    def BOARD_ROOT():
        return "http://api.radio-browser.info/"
