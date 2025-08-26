console = { log: function(x) {call_python("log", x); } }
document = { querySelectorAll: function(s) {
    var handles = call_python("querySelectorAll", s);
    return handles.map(function(h) {return new Node(h)});
    }}

function Node(handle) {this.handle = handle;}

Node.prototype.getAttribute = function(attr) {
    return call_python("getAttribute", this.handle, attr);
}

LISTENERS = {}

Node.prototype.addEventListener = function(type, listener) {
    if (!LISTENERS[this.handle]) LISTENERS[this.handle] = {};
    var dict = LISTENERS[this.handle];
    if (!dict[type]) dict[type] = [];
    var list = dict[type];
    list.push(listener);
}

Node.prototype.dispatchEvent = function(type) {
    var handle = this.handle;
    var list = (LISTENERS[handle] && LISTENERS[handle][type]) || [];
    for (var i = 0; i < list.length; i++) {
        list[i].call(this);
    }
}

function lengthCheck() {
    var name = this.getAttribute("name");
    var value = this.getAttribute("value");
    if (value.length > 10) {
        console.log("Input " + name + " has too much text.")
    }
}

var inputs = document.querySelectorAll("input");
for (var i = 0; i < inputs.length; i++) {
    inputs[i].addEventListener("keydown", lengthCheck);
}

Object.defineProperty(Node.prototype, 'innerHTML', {
    set: function(s) {
        call_python("innerHTML_set", this.handle, s.toString())
    }
});