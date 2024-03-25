import socket
import json


def connect_to_ciel_server() -> socket.socket:
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.connect('/.ciel-ipc.sock')
    return s


def send_to_ciel_server(s: socket.socket, command: str):
    data = json.dumps({
        'jsonrpc': '2.0',
        'id': 1,
        'command': command,
    })
    header = f'Content-Length: {len(data)}\r\n\r\n'
    s.sendall(header.encode('utf-8'))
    s.sendall(data.encode('utf-8'))


def receive_from_ciel_server(s: socket.socket):
    buf = s.recv(4096)
    tag = b'Content-Length: '
    header, *parts = buf.splitlines()
    if header.startswith(header):
        length = int(header[len(tag):])
        body = b'\n'.join(parts)
        if length > 4096:
            buf = s.recv(length - 4096)
            body += buf
        return json.loads(body.decode('utf-8'))
