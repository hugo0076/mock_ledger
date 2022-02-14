#import socketio
#
#sio = socketio.AsyncServer()
#
#@sio.on('*')
#async def catch_all(event, sid, data):
#    print(f'event {event} happened, sid {sid}, data {data}')
#    pass
#
#@sio.event
#def connect(sid, environ, auth):
#    print('server connect ', sid)
#
#@sio.event
#def disconnect(sid):
#    print('server disconnect ', sid)
#
#
##sio.emit('my event', {'data': 'foobar'})

# set async_mode to 'threading', 'eventlet', 'gevent' or 'gevent_uwsgi' to
# force a mode else, the best mode is selected automatically from what's
# installed
async_mode = None

from flask import Flask, render_template
import socketio

sio = socketio.Server(async_mode=async_mode)
app = Flask(__name__)
app.wsgi_app = socketio.WSGIApp(sio, app.wsgi_app)

@app.route('/')
def index():
    return render_template('latency.html')

@sio.event
def ping_from_client(sid):
    sio.emit('pong_from_server', room=sid)

if __name__ == '__main__':
    app.run(threaded=True)
    while True:
        print('sending')
        sio.sleep(3)
        sio.emit('msg_from_server')