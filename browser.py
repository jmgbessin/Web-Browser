import socket
import ssl
# allows for encrypted HTTPS connections
import tkinter
import tkinter.font

WIDTH, HEIGHT = 800, 600
HSTEP, VSTEP = 13, 18
SCROLL_STEP = 100
FONTS = {}

class Browser:
    def __init__(self):
        self.window = tkinter.Tk()
        self.canvas = tkinter.Canvas(
            self.window,
            width = WIDTH,
            height = HEIGHT
        )
        self.canvas.pack()
        # tkinter peculiarity: packs the canvas within the window
        self.scroll = 0
        
        self.window.bind("<Down>", self.scrolldown)
        # binds a function to a specific keyboard key through tkinter
        self.window.bind("<Up>", self.scrollup)
        self.window.bind("<MouseWheel>", self.mousescroll)
        
    def draw(self):
        self.canvas.delete("all")
        for x, y, w, font in self.display_list:
            if y > self.scroll + HEIGHT: continue
            if y + VSTEP < self.scroll: continue
            self.canvas.create_text(x, y - self.scroll, text = w, anchor = 'nw',
                                    font = font)
        
    def load(self, url):
        body = url.request()
        text = lex(body)
        self.display_list = Layout(text).display_list
        self.draw()
        
    # down key or scroll event handler
    """ scrolldown is passed an event object as an argument by Tk, but since 
    scrolling down doesn't require any information about the key press besides 
    the fact that it happened, scrolldown ignores that event object. """
    def scrolldown(self, e):
        self.scroll += SCROLL_STEP
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


class Layout:
    def __init__(self, tokens):
        self.line = []
        self.display_list = []
        self.cursor_x = HSTEP
        self.cursor_y = VSTEP
        self.weight = "normal"
        self.style = "roman"
        self.size = 12
        
        for tok in tokens:
            self.token(tok)
        self.flush()
            
    def token(self, tok):
        if isinstance(tok, Text):
            for word in tok.text.split():
                self.word(word)
        elif tok.tag == "i":
            self.style = "italic"
        elif tok.tag == "/i":
            self.style = "roman"
        elif tok.tag == "b":
            self.weight = "bold"
        elif tok.tag == "/b":
            self.weight = "normal"
        elif tok.tag == "small":
            self.size -= 2
        elif tok.tag == "/small":
            self.size += 2
        elif tok.tag == "big":
            self.size += 4
        elif tok.tag == "/big":
            self.size -= 4
        elif tok.tag == "br":
            self.flush()
        elif tok.tag == "/p":
            self.flush()
            self.cursor_y += VSTEP
            
    def word(self, word):
        font = getfont(self.size, self.weight, self.style)
        w = font.measure(word)
        if self.cursor_x + w > WIDTH - HSTEP:
            self.flush()
        self.line.append((self.cursor_x, self.cursor_y, word, font))
        self.cursor_x += w + font.measure(" ")
        
    def flush(self):
        if not self.line: return
        # checks for empty line list
        metrics = [font.metrics() for x, y, word, font in self.line]
        max_ascent = max([metric["ascent"] for metric in metrics])
        baseline = self.cursor_y + 1.25 * max_ascent
        # lowers the basline to account for different size fonts
        # 1.25 * max_ascent takes into account the leading
        
        for x, y, word, font in self.line:
            new_y = baseline - font.metrics("ascent")
            # positions each word relative to the new baseline
            self.display_list.append((x, new_y, word, font))
            
        max_descent = max([metric["descent"] for metric in metrics])
        self.cursor_y = baseline + 1.25 * max_descent
        
        self.cursor_x = HSTEP
        self.line = []
        
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
        self.body = body
        self.unfinished = []
        self.SELF_CLOSING_TAGS = ["area", "base", "br", "col", "embed", "hr", 
                                  "img", "input", "link", "meta", "param", 
                                  "source", "track", "wbr"]
        
    def add_text(self, text):
        if text.isspace(): return
        """ HTMLParser interprets HTML newlines as text and tries to add it to 
        tree. Will not work for newline after thrown away doctype tag """
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
    body = URL(sys.argv[1]).request()
    nodes = HTMLParser(body).parse()
    print_tree(nodes)
    #Browser().load(URL(sys.argv[1]))
    #tkinter.mainloop()
    """ This enters a loop that looks like this:
    while True:
        for evt in pendingEvents():
            handleEvent(evt)
        drawScreen()
    """