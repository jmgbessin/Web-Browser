import dukpy

RUNTIME_JS = open("runtime.js").read()

class JSContext:
    def __init__(self):
        self.interp = dukpy.JSInterpreter()
        
        self.interp.evaljs(RUNTIME_JS)
        
        self.interp.export_function("log", print)
        
    def run(self, script, code):
        # try except block ensures browser doesn't crash due to Javascript crash
        try:
            return self.interp.evaljs(code)
        except dukpy.JSRuntimeError as e:
            print("Script", script, "crashed", e)