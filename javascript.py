import dukpy

RUNTIME_JS = open("runtime.js").read()

class JSContext:
    def __init__(self):
        self.interp = dukpy.JSInterpreter()
        self.interp.export_function("log", print)
        
    def run(self, code):
        try:
            return self.interp.evaljs(code)
        except dukpy.JSInterpreter as e:
            print("Script", script, "crashed", e)