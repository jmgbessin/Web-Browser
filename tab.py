from htmlparser import HTMLParser, Element, Text
from style import *
from utils import *
from layout import DocumentLayout
import urllib.parse
from javascript import JSContext
import dukpy

DEFAULT_STYLE_SHEET = CSSParser(open("browser.css").read()).parse()
# default browser stylesheet

class Tab:
    def __init__(self, tab_height):
        self.scroll = 0
        self.url = None
        self.tab_height = tab_height
        self.history = []
        self.focus = None
        
    def draw(self, canvas, offset):
        for cmd in self.display_list:
            if cmd.rect.top > self.scroll + self.tab_height: continue
            if cmd.rect.bottom < self.scroll: continue
            cmd.execute(self.scroll - offset, canvas)
        
    def load(self, url, payload = None):
        
        # Downloading javascript scripts
        scripts = [
            node.attributes["src"] for node
            in tree_to_list(self.nodes, [])
            if isinstance(node, Element)
            and node.tag == "script"
            and "src" in node.attributes]
        
        self.js = JSContext()
        for script in scripts:
            script_url = url.resolve(script)
            try:
                body = script_url.request()
            except:
                continue
            self.js.run(body)
        print("Script returned: ", dukpy.evaljs(body))
        
        
        
            
        
        """
        The CSS rule that gets added last overrides the previous if it already
        exists for a certain HTML element. Thus, in this function, CSS rules
        get added later if theyr have higher priority
        """
        self.scroll = 0
        self.url = url
        self.history.append(url)
        body = url.request(payload)
        self.nodes = HTMLParser(body).parse()
        # create an HTML tree by parsing the html body
        self.rules = DEFAULT_STYLE_SHEET.copy()
        
        # retrieve stylesheet links from HTML document
        # goes after the default style sheet to override its properties
        # thanks to the way the paint method is implemented
        # try except ignores stylesheets that failed to download but may hide
        # bugs
        links = [node.attributes["href"] 
                 for node in tree_to_list(self.nodes, [])
                 if isinstance(node, Element)
                 and node.tag == "link"
                 and node.attributes.get("rel") == "stylesheet"
                 and "href" in node.attributes]
        for link in links:
            style_url = url.resolve(link)
            try:
                body = style_url.request()
            except:
                print("failed a css stylesheet connection")
                continue
            self.rules.extend(CSSParser(body).parse())
            
        self.render()
        
    def render(self):
        """
        Adds CCS to nodes. Python's sorted function keeps the relative order 
        of things with equal priority, so file order acts as a tie breaker, 
        as it should.
        """
        style(self.nodes, sorted(self.rules, key = cascade_priority))
        
        # create a root for the layout tree whose child is the root HTML node
        self.document = DocumentLayout(self.nodes)
        
        # create the Layout tree by a recursive mirroring of the HTML tree
        self.document.layout()
        
        # aggregates all the display_lists, containing commands, for each 
        # layout block
        self.display_list = []
        paint_tree(self.document, self.display_list)
  
    def go_back(self):
        if len(self.history) > 1:
            self.history.pop()
            back = self.history.pop()
            self.load(back)
            
    def submit_form(self, elt):
        inputs = [
            node for node in tree_to_list(elt, []) 
            if isinstance(node, Element)
            and node.tag == "input"
            and "name" in node.attributes]
        
        body = ""
        for input in inputs:
            name = input.attributes["name"]
            value = input.attributes.get("value", "")
            
            # percent encodes name and value to avoid running into trouble
            # with the characters & and =
            name = urllib.parse.quote(name)
            value = urllib.parse.quote(value)
            
            body += "&" + name + "=" + value
        body = body[1:]
        
        url = self.url.resolve(elt.attributes["action"])
        self.load(url, body)

    # down key or scroll event handler
    """ scrolldown is passed an event object as an argument by Tk, but since 
    scrolling down doesn't require any information about the key press besides 
    the fact that it happened, scrolldown ignores that event object. """
    def scrolldown(self):
        max_y = max(self.document.height + 2 * VSTEP - self.tab_height, 0)
        self.scroll = min(self.scroll + SCROLL_STEP, max_y)
        
    def scrollup(self):
        if self.scroll < SCROLL_STEP:
            self.scroll = 0
        else:
            self.scroll -= SCROLL_STEP
        
    def mousescroll(self, delta):
        if delta < 0:
            self.scrolldown()
        else:
            self.scrollup()
            
    def click(self, x, y):
        self.focus = None
        y += self.scroll
        
        objs = [obj for obj in tree_to_list(self.document, [])
                if obj.x <= x < obj.x + obj.width
                and obj.y <= y < obj.y + obj.height]
        if not objs: return
        
        # we go to the end of the list because we want the most specific element
        # that was clicked
        elt = objs[-1].node
        
        if self.focus:
            self.focus.is_focused = False
        while elt:
            if isinstance(elt, Text):
                pass
            elif elt.tag == "a" and "href" in elt.attributes:
                url = self.url.resolve(elt.attributes["href"])
                return self.load(url)
            elif elt.tag == "input":
                self.focus = elt
                elt.attributes["value"] = ""
                elt.is_focused = True
                return self.render()
            elif elt.tag == "button":
                while elt:
                    if elt.tag == "form" and "action" in elt.attributes:
                        return self.submit_form(elt)
                    elt = elt.parent
            elt = elt.parent
        self.render()
        
    def keypress(self, char):
        if self.focus:
            self.focus.attributes["value"] += char
            self.render()
