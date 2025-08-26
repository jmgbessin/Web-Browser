import dukpy
from style import CSSParser
from utils import *

RUNTIME_JS = open("runtime.js").read()

class JSContext:
    def __init__(self, tab):
        self.interp = dukpy.JSInterpreter()
        self.tab = tab
        
        self.interp.evaljs(RUNTIME_JS)
        
        self.interp.export_function("log", print)
        self.interp.export_function("querySelectorAll", self.querySelectorAll)
        self.interp.export_function("getAttribute", self.getAtribute)
        
        self.node_to_handle = {}
        self.handle_to_node = {}
        
    def run(self, script, code):
        # try except block ensures browser doesn't crash due to Javascript crash
        try:
            return self.interp.evaljs(code)
        except dukpy.JSRuntimeError as e:
            print("Script", script, "crashed", e)
            
    def querySelectorAll(self, selector_text):
        selector = CSSParser(selector_text).selector()
        nodes = [
            node for node in tree_to_list(self.tab.nodes, [])
            if selector.matches(node)
            ]
        return [self.get_handle(node) for node in nodes]
    
    def get_handle(self, elt):
        if elt not in self.node_to_handle:
            handle = len(self.node_to_handle)
            self.node_to_handle[elt] = handle
            self.handle_to_node[handle] = elt
        else:
            handle = self.node_to_handle[elt]
        return handle
    
    def getAtribute(self, handle, attr):
        elt = self.handle_to_node[handle]
        attr = elt.attributes.get(attr, None)
        return attr if attr else ""
            
        