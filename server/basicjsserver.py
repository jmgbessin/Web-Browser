import socket

def handle_connection(conx):
    # the request line
    req = conx.makefile("b")
    reqline = req.readline().decode('utf8')
    method, url, version = reqline.split(" ", 2)
    assert method in ["GET", "POST"]
    
    headers = {}
    while True:
        line = req.readline().decode('utf8')
        if line == '\r\n': break
        header, value = line.split(":", 1)
        headers[header.casefold()] = value.strip()
        
    if 'content-length' in headers:
        length = int(headers['content-length'])
        body = req.read(length).decode('utf8')
    else:
        body = None
    
    status, body = do_request(method, url, headers, body)
    print("do_request:\n")
    print(status)
    print(body)
    print("\n")
    
    response = "HTTP/1.0 {}\r\n".format(status)
    response += "Content-Length: {}\r\n".format(
        len(body.encode('utf8'))
    )
    response += "\r\n" + body
    conx.send(response.encode('utf8'))
    conx.close()
    
def do_request(method, url, headers, body):
    if method == "GET" and url == "/":
        return "200 OK", display_webpage()
    elif method == "GET" and url == "/test.js":
        with open("test.js") as f:
            return "200 OK", f.read()
    else:
        return "404 Not found"

def display_webpage():
    return "<script src=test.js></script>"

s = socket.socket(
    family = socket.AF_INET,
    type = socket.SOCK_STREAM,
    proto = socket.IPPROTO_TCP
)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) 

""" instead of calling connect to connect to a server we call bind which waits 
for a computer to connect - the first argument specifies who can connect: it
being empty means anyone can - the second argument is the port others must use
to talk to our server: ports below 1024 require administrative priviledges, so
8000 was arbitraily chosen """
s.bind(('', 8000))
# the listen call tells the OS that we're ready to accept connections
s.listen()

# to accept those connections, we enter a loop that runs once per connection
while True:
    conx, addr = s.accept()
    handle_connection(conx)
    
