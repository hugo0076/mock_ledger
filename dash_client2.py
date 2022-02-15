from dash import Dash, dash_table
from dash import dcc
from dash import html
from dash.dependencies import Input, Output, State
import plotly.express as px
import socket
import pandas as pd
from collections import OrderedDict
import sys
import plotly.graph_objects as go
import numpy as np
from random import random

from data_types import Order

import asyncio
import time
import socketio
from collections import defaultdict
import json
from types import SimpleNamespace

# loop = asyncio.get_event_loop()
sio = socketio.Client()

def send_ping():
    sio.emit('ping_from_client')

@sio.event
def connect():
    print('connected to server')

@sio.on('*')
def catch_all(event, raw_data):
    data = json.loads(raw_data, object_hook=lambda d: SimpleNamespace(**d))
    if event == 'insert':
        print(f'got insrt {data}')
        serv.handle_order(data)
    elif event == 'trade':
        print(f'got trade: {data}')
        serv.handle_trade(data)
    pass

def start_server():
    sio.connect('http://localhost:5000')
    print('blah')

class Server():

    def __init__(self) -> None:
        self.order_book = []
        self.order_book_df = pd.DataFrame()
        self.bids = []
        self.asks = []
        # TODO: add code to get current state of book
        print('init')
    
    def handle_order(self, order):
        # if not add to book 
        self.order_book.append(order)
        if order.o_type == 'BID':
            self.bids.append(order)
        elif order.o_type == 'ASK':
            self.asks.append(order)
        return 0
    
    def handle_trade(self, trade):
        # if not add to book 
        if trade.resting_order not in [t.id for t in self.order_book]:
            print('Oops, we dont have a copy of the resting order')
            raise IndexError
        print(f'ob: {len(self.order_book)} bid: {len(self.bids)} ask: {len(self.asks)}')
        self.order_book = [order for order in self.order_book if order.id != trade.resting_order]
        if trade.resting_order_type == 'BID':
            self.bids = [order for order in self.bids if order.id != trade.resting_order]
        elif trade.resting_order_type == 'ASK':
            self.asks = [order for order in self.asks if order.id != trade.resting_order]
        return 0

    def main(self, type = 0):
        print('launching dash')
        es = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
        app = Dash(__name__, external_stylesheets=es)
        bid_quote_input = [
            html.Div(dcc.Input(id='input-on-submit-bid', type='text')),
            html.Button('Submit Bid', id='bid-quote-val'),
            html.Div(id='container-button-basic-bid',
                     children='Enter a bid and press submit')
        ]
        ask_quote_input = [
            html.Div(dcc.Input(id='input-on-submit-ask', type='text')),
            html.Button('Submit Ask', id='ask-quote-val'),
            html.Div(id='container-button-basic-ask',
                     children='Enter an offer and press submit')
        ]

        data_dict = OrderedDict(
            [
                ("Bids Qty", [0,0,0,0,1, 2, 4, 2]),
                ("Price", [i for i in range(200,280,10)]),
                ("Asks Qty", [1, 2, 4, 2,0,0,0,0])
            ]
        )

        data = pd.DataFrame(data_dict)

        #x0 = np.random.randn(500)
        ## Add 1 to shift the mean of the Gaussian distribution
        #x1 = np.random.randn(500) + 1
        #
        #fig = go.Figure()
        #fig.add_trace(go.Histogram(x=x0))
        #fig.add_trace(go.Histogram(x=x1))
        #
        ## Overlay both histograms
        #fig.update_layout(barmode='overlay')
        ## Reduce opacity to see both histograms
        #fig.update_traces(opacity=0.75)
        #fig.show()

        app.layout = html.Div(children=[
            html.Div([
                dcc.Interval(id='refresh_ui', interval=2000, n_intervals=0),
                html.H1(id='labelUI', children='')
            ]),
            #html.Div([
            #    dcc.Interval(id='send_order', interval=5500, n_intervals=0),
            #    html.H1(id='labelSO', children='')
            #]),

            dcc.Store(id='order_book', data = []),

            html.H1(children='Mock Ledger'),

            html.Div(children='''
                Dash: A web application framework for your data.
            '''),

            dcc.Graph(id="graph"),

            html.Div([
                dash_table.DataTable(
                    id='table',
                    style_data={
                        'width': '10px',
                        'maxWidth': '10px',
                        'minWidth': '10px',
                    },
                    columns=[{"name": i, "id": i} 
                             for i in data.columns],
                    data=data.to_dict('records'),
                    style_cell=dict(textAlign='left'),
                    style_header=dict(backgroundColor="paleturquoise")
                )
            ], style={'width' : '50%', 'align' : 'center', 'flex': 1}),

            html.Div(
                bid_quote_input + ask_quote_input
            )
        ])

        @app.callback(
            Output("graph", "figure"),
            Input('refresh_ui', 'n_intervals'))
        def display_color(mean = 0):
            bid_px_q = []
            for order in self.bids:
                bid_px_q += [order.price] * int(order.qty)
            bid_px_q.sort(key = lambda x: float(x))
            ask_px_q = []
            for order in self.asks:
                ask_px_q += [order.price] * int(order.qty)
            ask_px_q.sort(key = lambda x: float(x))
            #data_bid = np.random.normal(200, 15, size=500)
            #data_ask = np.random.normal(100, 15, size=500)
            fig = go.Figure()
            #bins = dict(start=0, end=475, size=15)
            fig.add_trace(go.Histogram(x=bid_px_q))
            fig.add_trace(go.Histogram(x=ask_px_q))

            # Overlay both histograms
            fig.update_layout(barmode='overlay')
            return fig

        @app.callback(
            Output('container-button-basic-bid', 'children'),
            Input('bid-quote-val', 'n_clicks'),
            State('input-on-submit-bid', 'value')
        )
        def update_output_bid(n_clicks, value):
            if not value == None:
                print(f'Sending buy request at ${value}')
                sio.emit('BID', [value,1])
            return 'Input "{}"'.format(
                value
            )
        @app.callback(
            Output('container-button-basic-ask', 'children'),
            Input('ask-quote-val', 'n_clicks'),
            State('input-on-submit-ask', 'value')
        )
        def update_output_ask(n_clicks, value):
            if not value == None:
                print(f'Sending ask request at ${value}')
                sio.emit('ASK', [value,1])
            return 'Input "{}"'.format(
                value
            )

        @app.callback(Output('labelUI', 'children'),
            [Input('refresh_ui', 'n_intervals')])
        def update_interval(n):
            print(f'query:{n}')
            #sio.emit('BID', [200,3])
            return ''

        #@app.callback(Output('labelSO', 'children'),
        #    [Input('send_order', 'n_intervals')])
        #def update_interval(n):
        #    print(f'query:{n}')
        #    sio.emit('BID', [200,3])
        #    return ''
        port = 4000 + round(1000*random())
        app.run_server(port=port, debug=True)


if __name__ == '__main__':
    serv = Server()
    start_server()
    print('trying main')
    serv.main()
    #while True:
    #    sio.emit('my message', {'foo': 'bar'})
    #    time.wait(1)
    #main(int(sys.argv[1]))
   