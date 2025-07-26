import tkinter
import time
from chrome import Chrome
from utils import *
from draw import *
from url import URL
from layout import *
from tab import Tab


class Browser:
    def __init__(self):
        self.tabs = []
        self.active_tab = None
        
        self.window = tkinter.Tk()
        self.canvas = tkinter.Canvas(
            self.window,
            width = WIDTH,
            height = HEIGHT,
            bg = "white"
        )
        # tkinter peculiarity: packs the canvas within the window
        self.canvas.pack()
        
        self.window.bind("<Down>", self.handle_down)
        # binds a function to a specific keyboard key through tkinter
        self.window.bind("<Up>", self.handle_up)
        self.window.bind("<MouseWheel>", self.handle_scroll)
        self.window.bind("<Button-1>", self.handle_click)
        self.window.bind("<Key>", self.handle_key)
        self.window.bind("<Return>", self.handle_enter)
        
        self.chrome = Chrome(self)
        
    def draw(self):
        self.canvas.delete("all")
        self.active_tab.draw(self.canvas, self.chrome.bottom)
        for cmd in self.chrome.paint():
            cmd.execute(0, self.canvas)
        
    def new_tab(self, url):
        new_tab = Tab(HEIGHT - self.chrome.bottom)
        new_tab.load(url)
        self.active_tab = new_tab
        self.tabs.append(new_tab)
        self.draw()
        
    def handle_down(self, e):
        self.active_tab.scrolldown()
        self.draw()
        
    def handle_up(self, e):
        self.active_tab.scrollup()
        self.draw()
        
    def handle_scroll(self, e):
        self.active_tab.mousescroll(e.delta)
        self.draw()
        
    def handle_click(self, e):
        self.chrome.focus = None
        if e.y < self.chrome.bottom:
            self.focus = None
            self.chrome.click(e.x, e.y)
        else:
            self.focus = "content"
            self.chrome.blur()
            tab_y = e.y - self.chrome.bottom
            self.active_tab.click(e.x, tab_y)
        self.draw()
        
    def handle_key(self, e):
        if len(e.char) == 0: return
        if not (0x20 <= ord(e.char) < 0x7f): return
        self.chrome.keypress(e.char)
        self.draw()
        if self.chrome.keypress(e.char):
            self.draw()
        elif self.focus == "content":
            self.active_tab.keypress(e.char)
            self.draw()
        
    def handle_enter(self, e):
        self.chrome.enter()
        self.draw()


if __name__ == "__main__":
    import sys
    time.sleep(0.5)
    Browser().new_tab(URL(sys.argv[1]))
    tkinter.mainloop()
    """ This enters a loop that looks like this:
    while True:
        for evt in pendingEvents():
            handleEvent(evt)
        drawScreen()
    """