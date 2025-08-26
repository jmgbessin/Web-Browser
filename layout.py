from draw import *
from htmlparser import Text, Element
from utils import *

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
        
    def __repr__(self):
        return self.node.tag
        
    def self_rect(self):
        return Rect(self.x, self.y, self.x + self.width, self.y + self.height)
        
    def layout_mode(self):
        if isinstance(self.node, Text):
            return "inline"
        elif any([isinstance(child, Element) and \
            child.tag in BLOCK_ELEMENTS for child in self.node.children]):
            return "block"
        elif self.node.children or self.node.tag == "input":
            return "inline"
        else:
            return "block"
        
    def should_paint(self):
        return isinstance(self.node, Text) or \
            (self.node.tag != "input" and self.node.tag != "button")
        
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
        
    def new_line(self):
        self.cursor_x = 0
        last_line = self.children[-1] if self.children else None
        new_line = LineLayout(self.node, self, last_line)
        self.children.append(new_line)
    
    def recurse(self, node):
        if isinstance(node, Text):
            for word in node.text.split():
                self.word(node, word)
        else:
            if node.tag == "br":
                self.new_line()
            elif node.tag == "input" or node.tag == "button":
                self.input(node)
            if isinstance(node, Element) and not node.tag == "button":
                for child in node.children:
                    self.recurse(child)
                
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
        self.cursor_x += w + font.measure(" ")
                
    def input(self, node):
        w = INPUT_WIDTH_PX
        if self.cursor_x + w > self.width:
            self.new_line()
        line = self.children[-1]
        previous_word = line.children[-1] if line.children else None
        input = InputLayout(node, line, previous_word)
        line.children.append(input)
        
        weight = node.style["font-weight"]
        style = node.style["font-style"]
        if style == "normal": style = "roman"
        size = int(float(node.style["font-size"][:-2]) * .75)
        font = getfont(size, weight, style)
        
        self.cursor_x += w + font.measure(" ")

    def paint(self):
        cmds = []
        
        bgcolor = self.node.style.get("background-color", "transparent")
        if bgcolor != "transparent":
            x2, y2 = self.x + self.width, self.y + self.height
            rect = DrawRect(self.self_rect(), bgcolor)
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
        
    def should_paint(self):
        return True
        
    def paint(self):
        return []
    
    
class LineLayout:
    def __init__(self, node, parent, previous):
        self.node = node
        self.parent = parent
        self.previous = previous
        self.children = []
        
    def __repr__(self):
        return "line"
        
    def layout(self):
        self.width = self.parent.width
        self.x = self.parent.x
        
        if self.previous:
            self.y = self.previous.y + self.previous.height
        else:
            self.y = self.parent.y
            
        for word in self.children:
            word.layout()
        
        if not self.children:
            pass
        
        # current patch: add 0 to list in case a paragraph is empty
        max_ascent = max([word.font.metrics("ascent") 
                          for word in self.children] + [0])
        baseline = self.y + 1.25 * max_ascent
        for word in self.children:
            word.y = baseline - word.font.metrics("ascent")
        # same
        max_descent = max([word.font.metrics("descent") 
                           for word in self.children] + [0])
        
        self.height = 1.25 * (max_ascent + max_descent)
        
    def should_paint(self):
        return True
        
    def paint(self):
        return []
        
        
class TextLayout:
    def __init__(self, node, word, parent, previous):
        self.node = node
        self.word = word
        self.children = []
        self.parent = parent
        self.previous = previous
        
    def __repr__(self):
        return self.word
        
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
        
    def should_paint(self):
        return True
        
    def paint(self):
        color = self.node.style["color"]
        return [DrawText(self.x, self.y, self.word, self.font, color)]


INPUT_WIDTH_PX = 200

    
class InputLayout:
    def __init__(self, node, parent, previous):
        self.node = node
        self.children = []
        self.parent = parent
        self.previous = previous
        
    def layout(self):
        weight = self.node.style["font-weight"]
        style = self.node.style["font-style"]
        if style == "normal": style = "roman"
        size = int(float(self.node.style["font-size"][:-2]) * .75)
        self.font = getfont(size, weight, style)
        
        self.width = INPUT_WIDTH_PX
        
        if self.previous:
            space = self.font.measure(" ")
            self.x = self.previous.x + space + self.previous.width
        else:
            self.x = self.parent.x
            
        self.height = self.font.metrics("linespace")
        
    def should_paint(self):
        return True
    
    def self_rect(self):
        return Rect(self.x, self.y, self.x + self.width, self.y + self.height)
        
    def paint(self):
        cmds = []
        bgcolor = self.node.style.get(
            "background-color", 
            "transparent")
        if bgcolor != "transparent":
            rect = DrawRect(self.self_rect(), bgcolor)
            cmds.append(rect)
            
        if self.node.tag == "input":
            text = self.node.attributes.get("value", "")
        elif self.node.tag == "button":
            if len(self.node.children) == 1 and \
                isinstance(self.node.children[0], Text):
                    text = self.node.children[0].text
            else:
                print("Ignoring HTML contents inside button")
                text = ""
                
        color = self.node.style["color"]
        cmds.append(
            DrawText(self.x, self.y, text, self.font, color)
        )
        
        if self.node.is_focused:
            cx = self.x + self.font.measure(text)
            cmds.append(DrawLine(
                cx, self.y, cx, self.y + self.height, "black", 1
            ))
                
        return cmds