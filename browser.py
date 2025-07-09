import socket
import ssl
# allows for encrypted HTTPS connections
import tkinter
import tkinter.font
import time

WIDTH, HEIGHT = 800, 600
HSTEP, VSTEP = 13, 18
SCROLL_STEP = 100
FONTS = {}

def tree_to_list(tree, list):
    list.append(tree)
    for child in tree.children:
        tree_to_list(child, list)
    return list


class Browser:
    def __init__(self):
        self.window = tkinter.Tk()
        self.canvas = tkinter.Canvas(
            self.window,
            width = WIDTH,
            height = HEIGHT,
            bg = "white"
        )
        self.canvas.pack()
        # tkinter peculiarity: packs the canvas within the window
        self.scroll = 0
        
        self.window.bind("<Down>", self.scrolldown)
        # binds a function to a specific keyboard key through tkinter
        self.window.bind("<Up>", self.scrollup)
        self.window.bind("<MouseWheel>", self.mousescroll)
        self.window.bind("<Button-1>", self.click)
        
        self.url = None
        
    def draw(self):
        self.canvas.delete("all")
        for cmd in self.display_list:
            if cmd.top > self.scroll + HEIGHT: continue
            if cmd.bottom < self.scroll: continue
            cmd.execute(self.scroll, self.canvas)
        
    def load(self, url):
        """
        The CSS rule that gets added last overrides the previous if it already
        exists for a certain HTML element. Thus, in this function, CSS rules
        get added later if theyr have higher priority
        """
        self.scroll = 0
        self.url = url
        body = url.request()
        self.nodes = HTMLParser(body).parse()
        # create an HTML tree by parsing the html body
        rules = DEFAULT_STYLE_SHEET.copy()
        
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
            rules.extend(CSSParser(body).parse())
        
        # add CSS to nodes
        """
        Python's sorted function keeps the relative order of things with equal 
        priority, so file order acts as a tie breaker, as it should.
        """
        style(self.nodes, sorted(rules, key = cascade_priority))
        
        # create a root for the layout tree whose child is the root HTML node
        self.document = DocumentLayout(self.nodes)
        
        # create the Layout tree by a recursive mirroring of the HTML tree
        self.document.layout()
        
        self.display_list = []
        paint_tree(self.document, self.display_list)
        # aggregates all the display_lists, containing commands, for each 
        # layout block
        self.draw()

    # down key or scroll event handler
    """ scrolldown is passed an event object as an argument by Tk, but since 
    scrolling down doesn't require any information about the key press besides 
    the fact that it happened, scrolldown ignores that event object. """
    def scrolldown(self, e):
        max_y = max(self.document.height + 2 * VSTEP - HEIGHT, 0)
        self.scroll = min(self.scroll + SCROLL_STEP, max_y)
        self.draw()
        
    def scrollup(self, e):
        if self.scroll < SCROLL_STEP:
            self.scroll = 0
        else:
            self.scroll -= SCROLL_STEP
        self.draw()
        
    def mousescroll(self, e):
        if e.delta < 0:
            self.scrolldown(e)
        else:
            self.scrollup(e)
            
    def click(self, e):
        x, y = e.x, e.y
        y += self.scroll
        
        objs = [obj for obj in tree_to_list(self.document, [])
                if obj.x <= x < obj.x + obj.width
                and obj.y <= y < obj.y + obj.height]
        if not objs: return
        
        # we go to the end of the list because we want the most specific element
        # that was clicked
        elt = objs[-1].node
        
        while elt:
            if isinstance(elt, Text):
                pass
            elif elt.tag == "a" and "href" in elt.attributes:
                url = self.url.resolve(elt.attributes["href"])
                return self.load(url)
            elt = elt.parent


class DrawText:
    def __init__(self, x1, y1, text, font, color):
        self.top = y1
        self.left = x1
        self.text = text
        self.font = font
        self.color = color
        self.bottom = y1 + font.metrics("linespace")
    
    def execute(self, scroll, canvas):
        canvas.create_text(
            self.left, 
            self.top - scroll, 
            text = self.text,
            font = self.font, 
            anchor = 'nw',
            fill = self.color)


class DrawRect:
    def __init__(self, x1, y1, x2, y2, color):
        self.top = y1
        self.left = x1
        self.bottom = y2
        self.right = x2
        self.color = color
        
    def execute(self, scroll, canvas):
        canvas.create_rectangle(
            self.left, 
            self.top - scroll,
            self.right,
            self.bottom - scroll,
            width = 0,
            fill = self.color)


BLOCK_ELEMENTS = ["html", "body", "article", "section", "nav", "aside", "h1", 
                  "h2", "h3", "h4", "h5", "h6", "hgroup", "header", "footer",
                  "address", "p", "hr", "pre", "blockquote", "ol", "ul", "menu",
                  "li", "dl", "dt", "dd", "figure", "figcaption", "main", "div",
                  "table", "form", "fieldset", "legend", "details", "summary"]
# as opposed to text-related tags like <b> - taken from HTML living standard


class BlockLayout:
    def __init__(self, node, parent, previous):
        self.node = node
        self.parent = parent
        self.previous = previous
        # Having a pointer to the previous sibling is useful
        self.children = []
        
        self.x = None
        self.y = None
        self.width = None
        self.height = None
        
    def layout_mode(self):
        if isinstance(self.node, Text):
            return "inline"
        elif any([isinstance(child, Element) and \
            child.tag in BLOCK_ELEMENTS for child in self.node.children]):
            return "block"
        elif self.node.children:
            return "inline"
        else:
            return "block"
        
    def layout(self):
        self.x = self.parent.x
        self.width = self.parent.width
        if self.previous:
            self.y = self.previous.y + self.previous.height
        else:
            self.y = self.parent.y

        mode = self.layout_mode()
        if mode == "block":
            previous = None
            for child in self.node.children:
                next = BlockLayout(child, self, previous)
                self.children.append(next)
                previous = next
        else:
            
            self.cursor_x = 0
            self.weight = "normal"
            self.style = "roman"
            self.size = 12
            
            self.new_line()
            self.recurse(self.node)
        
        for child in self.children:
            child.layout()
            
        self.height = sum([child.height for child in self.children])

    def open_tag(self, tag):
        if tag == "i":
            self.style = "italic"
        elif tag == "b":
            self.weight = "bold"
        elif tag == "small":
            self.size -= 2
        elif tag == "big":
            self.size += 4
        elif tag == "br":
            self.flush()
            
    def close_tag(self, tag):
        if tag == "i":
            self.style = "roman"
        elif tag == "b":
            self.weight = "normal"
        elif tag == "small":
            self.size += 2
        elif tag == "big":
            self.size -= 4
        elif tag == "p":
            self.flush()
            self.cursor_y += VSTEP
            
    def word(self, node, word):
        color = node.style["color"]
        if color == "#04a":
            print("received a blue font color command")
        weight = node.style["font-weight"]
        style = node.style["font-style"]
        if style == "normal": style = "roman"
        # CSS pixels are converted to Tk points, hence the .75 constant
        size = int(float(node.style["font-size"][:-2]) * .75)
        font = getfont(size, weight, style)
        w = font.measure(word)
        if self.cursor_x + w > self.width:
            self.new_line()
                
        # the current line is the last LineLayout child of BlockLayout
        line = self.children[-1]
        previous_word = line.children[-1] if line.children else None
        text = TextLayout(node, word, line, previous_word)
        line.children.append(text)
        
    def new_line(self):
        self.cursor_x = 0
        last_line = self.children[-1] if self.children else None
        new_line = LineLayout(self.node, self, last_line)
        self.children.append(new_line)
        
    def flush(self):
        if not self.children: return
        # checks for empty line list
        metrics = [font.metrics() for x, word, font, color in self.line]
        
        # lowers the basline to account for different size fonts
        # 1.25 * max_ascent takes into account the leading
        
        for rel_x, word, font, color in self.line:
            x = self.x + rel_x
            y = self.y + baseline - font.metrics("ascent")
            # positions each word relative to the new baseline
            self.display_list.append((x, y, word, font, color))
            
        max_descent = max([metric["descent"] for metric in metrics])
        self.cursor_y = baseline + 1.25 * max_descent
        
        self.cursor_x = 0
        self.line = []
    
    def recurse(self, node):
        if isinstance(node, Text):
            for word in node.text.split():
                self.word(node, word)
        else:
            if node.tag == "br":
                print("br tag new line")
                self.new_line()
            for child in node.children:
                self.recurse(child)

    def paint(self):
        cmds = []
        
        bgcolor = self.node.style.get("background-color", "transparent")
        if bgcolor != "transparent":
            x2, y2 = self.x + self.width, self.y + self.height
            rect = DrawRect(self.x, self.y, x2, y2, bgcolor)
            cmds.append(rect)

        return cmds


class DocumentLayout:
    def __init__(self, node):
        self.node = node
        self.parent = None
        self.children = []
        
        self.x = None
        self.y = None
        self.width = None
        self.height = None
        
    def layout(self):
        child = BlockLayout(self.node, self, None)
        self.children.append(child)

        self.width = WIDTH - 2 * HSTEP
        self.x = HSTEP
        self.y = VSTEP
        child.layout()
        self.height = child.height
        
    def paint(self):
        return []
    
    
class LineLayout:
    def __init__(self, node, parent, previous):
        self.node = node
        self.parent = parent
        self.previous = previous
        self.children = []
        
    def layout(self):
        self.width = self.parent.width
        self.x = self.parent.x
        
        if self.previous:
            self.y = self.previous.y + self.previous.height
        else:
            self.y = self.parent.y
            
        for word in self.children:
            word.layout()
            
        max_ascent = max([word.font.metrics("ascent") 
                          for word in self.children])
        baseline = self.y + 1.25 * max_ascent
        for word in self.children:
            word.y = baseline - word.font.metrics("ascent")
        max_descent = max([word.font.metrics("descent") 
                           for word in self.children])
        
        self.height = 1.25 * (max_ascent + max_descent)
        
    def paint(self):
        return []
        
        
class TextLayout:
    def __init__(self, node, word, parent, previous):
        self.node = node
        self.word = word
        self.children = []
        self.parent = parent
        self.previous = previous
        
    def layout(self):
        weight = self.node.style["font-weight"]
        style = self.node.style["font-style"]
        if style == "normal": style = "roman"
        size = int(float(self.node.style["font-size"][:-2]) * .75)
        self.font = getfont(size, weight, style)
        
        self.width = self.font.measure(self.word)
        
        if self.previous:
            space = self.font.measure(" ")
            self.x = self.previous.x + space + self.previous.width
        else:
            self.x = self.parent.x
            
        self.height = self.font.metrics("linespace")
        
    def paint(self):
        color = self.node.style["color"]
        return [DrawText(self.x, self.y, self.word, self.font, color)]


def style(node, rules):
    node.style = {}
    """inherited styles come first because they should be overriden by explicit
    rules"""
    for property, default_value in INHERITED_PROPERTIES.items():
        if node.parent:
            node.style[property] = node.parent.style[property]
        else:
            node.style[property] = default_value

    # stylings that come from CSS file
    for selector, body in rules:
        if not selector.matches(node): continue
        for property, value in body.items():
            node.style[property] = value
    
    # stylings that come from HTML "style" tag attrribute
    if isinstance(node, Element) and "style" in node.attributes:
        pairs = CSSParser(node.attributes["style"]).body()
        for property, value in pairs.items():
            node.style[property] = value
            
    """
    Converts percentage fonts to pixel fonts. This happens after all style
    values have been handled but before we recurse, so that any children
    can assume their parent's font size has been resolved to a pixel value 
    """
    if node.style["font-size"].endswith("%"):
        if node.parent:
            parent_font_size = node.parent.style["font-size"]
        else:
            parent_font_size = INHERITED_PROPERTIES["font-size"]
        node_pct = float(node.style["font-size"][:-1]) / 100
        parent_px = float(parent_font_size[:-2])
        node.style["font-size"] = str(node_pct * parent_px) + "px"
    
    for child in node.children:
        style(child, rules)

def paint_tree(layout_object, display_list):
    display_list.extend(layout_object.paint())
    for child in layout_object.children:
        paint_tree(child, display_list)

 
class Text:
    def __init__(self, text, parent):
        self.text = text
        self.children = []
        self.parent = parent
        
    def __repr__(self):
        return repr(self.text)
    
        
class Element:
    def __init__(self, tag, attributes, parent):
        self.tag = tag
        self.attributes = attributes
        self.children = []
        self.parent = parent
    
    def __repr__(self):
        return "<" + self.tag + ">"


class HTMLParser:
    def __init__(self, body):
        self.HEAD_TAGS = ["base", "basefont", "bgsound", "noscript", "link", "meta",
                     "title", "style", "script"]
        self.body = body
        self.unfinished = []
        self.SELF_CLOSING_TAGS = ["area", "base", "br", "col", "embed", "hr", 
                                  "img", "input", "link", "meta", "param", 
                                  "source", "track", "wbr"]
        
    def implicit_tags(self, tag):
        while True:
            open_tags = [node.tag for node in self.unfinished]
            if open_tags == [] and tag != "html":
                self.add_tag("html")
            elif open_tags == ["html"] and tag not in ["head", "body", "/html"]:
                if tag in self.HEAD_TAGS:
                    self.add_tag("head")
                else:
                    self.add_tag("body")
            elif open_tags == ["html", "head"] and \
                tag not in ["/head"] + self.HEAD_TAGS:
                self.add_tag("/head")
            else:
                break
    
    def add_text(self, text):
        if text.isspace(): return
        """ HTMLParser interprets HTML newlines as text and tries to add it to 
        tree. Will not work for newline after thrown away doctype tag """
        self.implicit_tags(None)
        parent = self.unfinished[-1]
        node = Text(text, parent)
        parent.children.append(node)
        
    def get_attributes(self, text):
        parts = text.split()
        # we are ignoring values that contatin whitespace - more complicated
        tag = parts[0].casefold()
        attributes = {}
        for attrpair in parts[1:]:
            if "=" in attrpair:
                key, value = attrpair.split("=", 1)
                if len(value) > 2 and value[0] in ["'", "\""]:
                    value = value[1:-1]
                # strip value quotes if there are any
                attributes[key.casefold()] = value
            else:
                attributes[attrpair.casefold()] = ""
        return tag, attributes
        
    def add_tag(self, tag):
        tag, attributes = self.get_attributes(tag)
        if tag.startswith("!"): return
        # we are throwing out the doctype html tag
        self.implicit_tags(tag)
        if tag.startswith("/"):
            if len(self.unfinished) == 1: return
            node = self.unfinished.pop()
            parent = self.unfinished[-1]
            parent.children.append(node)
        elif tag in self.SELF_CLOSING_TAGS:
            parent = self.unfinished[-1]
            node = Element(tag, attributes, parent)
            parent.children.append(node)
        else:
            parent = self.unfinished[-1] if self.unfinished else None
            node = Element(tag, attributes, parent)
            self.unfinished.append(node)
            
    def finish(self):
        while len(self.unfinished) > 1:
            node = self.unfinished.pop()
            parent = self.unfinished[-1]
            parent.children.append(node)
        return self.unfinished.pop()
            
    def parse(self):
        text = ""
        in_tag = False
        for c in self.body:
            if c == "<":
                in_tag = True
                if text: self.add_text(text)
                text = ""
            elif c == ">":
                in_tag = False
                self.add_tag(text)
                text = ""
            else:
                text += c
        if not in_tag and text:
            self.add_text(text)
        return self.finish()


class TagSelector:
    def __init__(self, tag):
        self.tag = tag
        self.priority = 1
        
    def matches(self, node):
        return isinstance(node, Element) and self.tag == node.tag


class DescendantSelector:
    def __init__(self, ancestor, descendant):
        self.ancestor = ancestor
        self.descendant = descendant
        self.priority = ancestor.priority + descendant.priority
        
    def matches(self, node):
        if not self.descendant.matches(node): return False
        while node.parent:
            if self.ancestor.matches(node.parent): return True
            node = node.parent
        return False
    
    
def cascade_priority(rule):
    selector, body = rule
    return selector.priority


INHERITED_PROPERTIES = {
    "font-size": "16px",
    "font-style": "normal",
    "font-weight": "normal",
    "color": "black"
}


class CSSParser:
    def __init__(self, s):
        self.s = s
        self.i = 0
        
    def whitespace(self):
        while self.i < len(self.s) and self.s[self.i].isspace():
            self.i += 1
            
    def word(self):
        start = self.i
        while self.i < len(self.s):
            if self.s[self.i].isalnum() or self.s[self.i] in "#-.%":
                self.i += 1
            else:
                break
        if not (self.i > start):
            raise Exception("Parsing Error")
        return self.s[start:self.i]
    
    def literal(self, literal):
        if not (self.i < len(self.s) and self.s[self.i] == literal):
            raise Exception("Parsing Error")
        self.i += 1
        
    def pair(self):
        prop = self.word()
        self.whitespace()
        self.literal(":")
        self.whitespace()
        val = self.word()
        return prop.casefold(), val
    
    def ignore_until(self, chars):
        while self.i < len(self.s):
            if self.s[self.i] in chars:
                return self.s[self.i]
            else:
                self.i += 1
        return None
    
    def body(self):
        pairs = {}
        while self.i < len(self.s) and self.s[self.i] != "}":
            """ Digital principle or robustness principle - produce maximally
            conformant output but accept even minimally conformant input - 
            different CSS might not render in different browsers, so the 
            principle allows for pages to be displayed in any browser """
            try:
                prop, val = self.pair()
                pairs[prop.casefold()] = val
                self.whitespace()
                self.literal(";")
                self.whitespace()
            except Exception:
                why = self.ignore_until([";", "}"])
                if why == ";":
                    self.literal(";")
                    self.whitespace()
                else:
                    break
                
        return pairs
    
    def selector(self):
        out = TagSelector(self.word().casefold())
        self.whitespace()
        while self.i < len(self.s) and self.s[self.i] != "{":
            tag = self.word()
            descendant = TagSelector(tag.casefold())
            out = DescendantSelector(out, descendant)
            self.whitespace()
        return out
    
    def parse(self):
        rules = []
        while self.i < len(self.s):
            try:
                self.whitespace()
                selector = self.selector()
                self.literal("{")
                self.whitespace()
                body = self.body()
                self.literal("}")
                rules.append((selector, body))
            except Exception:
                why = self.ignore_until(["}"])
                if why == "}":
                    self.literal("}")
                    self.whitespace()
                else:
                    break
        return rules
    

DEFAULT_STYLE_SHEET = CSSParser(open("browser.css").read()).parse()
# default browser stylesheet

def print_tree(node, indent = 0):
    print(" " * indent, node)
    for child in node.children:
        print_tree(child, indent + 2)
        

def getfont(size, weight, style):
    key = (size, weight, style)
    if key not in FONTS:
        font = tkinter.font.Font(
            size = size,
            weight = weight,
            slant = style
        )
        label = tkinter.Label(font = font)
        # what does this do?
        FONTS[key] = (font, label)
    return FONTS[key][0]


class URL:
    def __init__(self, url):
        self.scheme, url = url.split("://", 1)
        assert self.scheme in ["http", "https"]
        if self.scheme == "http":
            self.port = 80
        if self.scheme == "https":
            self.port = 443
        
        if "/" not in url:
            url = url + "/"
        self.host, url = url.split("/", 1)
        
        # support for custom ports
        if ":" in self.host:
            self.host, port = self.host.split(":", 1)
            self.port = int(port)
        
        self.path = "/" + url
        
    def __repr__(self):
        return f"{self.scheme}://{self.host}:{str(self.port)}{self.path}"
        
    # resolve a relative url
    def resolve(self, url):
        if "://" in url: return URL(url)
        if not url.startswith("/"):
            dir, _ = self.path.rsplit("/", 1)
            while url.startswith("../"):
                _, url = url.split("/", 1)
                if "/" in dir:
                    dir, _ = dir.rsplit("/", 1)
            url = dir + "/" + url
        if url.startswith("//"):
            return URL(self.scheme + ":" + url)
        else:
            return  URL(self.scheme + "://" + self.host + \
                ":" + str(self.port) + url)
        
    def request(self):
        # create socket
        s = socket.socket(
            family = socket.AF_INET,
            type = socket.SOCK_STREAM,
            # computer can send arbitrary amounts of data
            proto = socket.IPPROTO_TCP,
        )
        
        # connect socket to host
        s.connect((self.host, self.port))
        # requires host and port - port depends on protocol used
        if self.scheme == "https":
            ctx = ssl.create_default_context()
            s = ctx.wrap_socket(s, server_hostname = self.host)
        
        # request data from host
        request = "GET {} HTTP/1.0\r\n".format(self.path)
        request += "Host: {}\r\n".format(self.host)
        request += "\r\n"
        s.send(request.encode("utf8"))
        
        # get server response
        response = s.makefile("r", encoding = "utf8", newline = "\r\n")
        """ the makefile method abstracts the loop that collects bytes as they 
        arrive from the server """
        statusline = response.readline()
        version, status, explanation = statusline.split(" ", 2)
        
        response_headers = {}
        while True:
            line = response.readline()
            if line == "\r\n":
                break
            header, value = line.split(":", 1)
            response_headers[header.casefold()] = value.strip()
            """ headers are case-sensitive - this normalizes them on our side 
            if they come from server with capitals - and whitespace is 
            insignificant in HTTP header values """
        assert "transfer-encoding" not in response_headers
        assert "content-encoding" not in response_headers
        # indicates data is being sent in an unusual way
        
        content = response.read()
        s.close()
        return content


if __name__ == "__main__":
    import sys
    time.sleep(0.5)
    Browser().load(URL(sys.argv[1]))
    tkinter.mainloop()
    """ This enters a loop that looks like this:
    while True:
        for evt in pendingEvents():
            handleEvent(evt)
        drawScreen()
    """