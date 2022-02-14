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
import eventlet
import socketio

sio = socketio.Server()
app = socketio.WSGIApp(sio)

@sio.event
def connect(sid, environ):
    print('connect ', sid)

@sio.on('*')
def catch_all(event, sid, data):
    print(f'caught {event} and {data} from {sid}')
    if event == 'BID' or event == 'OFFER':
        handle_order(event, sid, data)
    pass

@sio.event
def disconnect(sid):
    print('disconnect ', sid)

bids = []
asks = []
order_book = []


def handle_order(event, sid, data):
    order = {'type' : event, 'sid': sid, 'price': data[0], 'qty': data[1]}
    print('handling order')
    order_book.append(order)
    print(order_book)
    print('sending out data')
    sio.emit('update', order)
    return 0

if __name__ == '__main__':
    eventlet.wsgi.server(eventlet.listen(('', 5000)), app)