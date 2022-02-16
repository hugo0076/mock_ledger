from audioop import reverse
from traceback import print_tb
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
import math
from random import random

import asyncio
from flask import request
import time
import datetime
import socketio
from collections import defaultdict
import json
from types import SimpleNamespace
import jsonpickle
from typedefs_ob import Order, Trade, Trader, OrderBook, Settlement

# loop = asyncio.get_event_loop()
sio = socketio.Client()

def send_ping():
    sio.emit('ping_from_client')

@sio.event
def connect():
    print('connected to server')

@sio.on('*')
def catch_all(event, raw_data):
    data = jsonpickle.decode(raw_data)
    if event == 'insert':
        print(f'got insrt {data}')
        cli.handle_order(data)
    elif event == 'trade':
        print(f'got trade: {data}')
        cli.handle_trade(data)
    elif event == 'order_book':
        print(f'got ob: {data}')
        cli.update_order_book(data)
    elif event == 'settlement':
        print(f'got settlement')
        cli.print_settlement(data)
        sys.exit(0)
    pass

def start_server():
    sio.connect('http://localhost:5001')

class DashClient():

    def __init__(self) -> None:
        self.orders = []
        self.order_book_df = pd.DataFrame()
        self.bids = []
        self.bid_px_q = []
        self.asks = []
        self.ask_px_q = []
        self.tick_size = 1
        # TODO: add code to get current state of book
        sio.emit('get_order_book', [])
        print('init')
    
    def handle_order(self, order):
        # if not add to book 
        self.orders.append(order)
        if order.o_type == 'BID':
            self.bids.append(order)
        elif order.o_type == 'ASK':
            self.asks.append(order)
        return 0
    
    def print_settlement(self, settlement):
        # if not add to book 
        for trade_str in settlement.trades_text:
            print(trade_str)
        print(f'total pnl: {settlement.pnl}')
        sio.disconnect()
    
    def update_order_book(self, order_book):
        # if not add to book 

        self.bids = order_book.bids
        self.asks = order_book.asks
        self.orders = order_book.orders
        self.trades = order_book.trades
        self.tick_size = order_book.tick_size
        return 0
    
    def handle_trade(self, trade):
        # if not add to book 
        if trade.resting_order not in [t.id for t in self.orders]:
            print('Oops, we dont have a copy of the resting order')
            raise IndexError
        print(f'ob: {len(self.orders)} bid: {len(self.bids)} ask: {len(self.asks)}')
        self.trades.append(trade)
        self.orders = [order for order in self.orders if order.id != trade.resting_order]
        if trade.resting_order_type == 'BID':
            self.bids = [order for order in self.bids if order.id != trade.resting_order]
        elif trade.resting_order_type == 'ASK':
            self.asks = [order for order in self.asks if order.id != trade.resting_order]
        return 0

    def main(self, type = 0):
        print('launching dash')
        es = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
        dash_app = Dash(__name__, external_stylesheets=es)
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
        settle_input = [
            html.Button('SETTLE', id='settle_btn', n_clicks=0),
            html.Div(id='settle_text',
                     children='')
        ]

        data_dict = OrderedDict(
            [
                ("Bids Qty", [0,0,0,0,1, 2, 4, 2]),
                ("Price", [i for i in range(200,280,10)]),
                ("Asks Qty", [1, 2, 4, 2,0,0,0,0])
            ]
        )

        data = pd.DataFrame(data_dict)
        o_data_dict = OrderedDict(
            [
                ("Price", [0,0,0,0,1, 2, 4, 2]),
                ("Qty", [i for i in range(200,280,10)]),
                ("Time", [1, 2, 4, 2,0,0,0,0])
            ]
        )

        o_data = pd.DataFrame(o_data_dict)
        print(data.to_dict('records'))

        dash_app.layout = html.Div(children=[
            html.Div([
                dcc.Interval(id='refresh_ui', interval=2500, n_intervals=0),
                html.H1(id='labelUI', children='')
            ]),
            html.Div([
                dcc.Interval(id='refresh_ob', interval=15000, n_intervals=0),
                html.H1(id='labelOB', children='')
            ]),

            html.H1(children='Mock Ledger',style={'textAlign': 'center'}),

            dcc.Graph(id="graph"),

            html.Div([
                dash_table.DataTable(
                    id="table",
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
                bid_quote_input + ask_quote_input + settle_input
            ),
            dash_table.DataTable(
                id="market_orders",
                data=o_data.to_dict('records'),
                columns=[{'id': c, 'name': c} for c in o_data.columns],
                page_action='none',
                style_table={'height': '300px', 'overflowY': 'auto'}
            )
        ])

        @dash_app.callback(
            Output("graph", "figure"),
            Input('refresh_ui', 'n_intervals'))
        def display_color(mean = 0):
            price_list = [o.price for o in self.orders]
            if self.orders:
                data_range = np.arange(min(price_list), max(price_list) + 1, self.tick_size)
            else:
                data_range = range(0,2,1)

            bids_dd = defaultdict(lambda x: 0)
            for row in data_range:
                bids_dd[row] = 0
            for order in self.bids:
                bids_dd[order.price] += order.qty
            
            asks_dd = defaultdict(lambda x: 0)
            for row in data_range:
                asks_dd[row] = 0
            for order in self.asks:
                asks_dd[order.price] += order.qty
            
            fig = go.Figure()
            #if self.bids and self.asks:
            #    bins = go.histogram.XBins(end=self.ask_px_q[-1], size=tick_size, start=self.bid_px_q[0])#dict(start=0, end=475, size=15)
            #    fig.add_trace(go.Histogram(x=self.bid_px_q, xbins = bins))
            #    fig.add_trace(go.Histogram(x=self.ask_px_q, xbins = bins))
            #else:
            fig_b = go.Bar(
                x=list(data_range),
                y=list(bids_dd.values()),
                width=[self.tick_size for i in data_range] # customize width here
            )   
            fig_a = go.Bar(
                x=list(data_range),
                y=list(asks_dd.values()),
                width=[self.tick_size for i in data_range] # customize width here
            )
            
            fig.add_trace(fig_a)
            fig.add_trace(fig_b)
            # Overlay both histograms
            fig.update_layout(barmode='overlay')
            return fig
        
        @dash_app.callback(
            Output("table", "data"),
            Input('refresh_ui', 'n_intervals'))
        def display_table(mean = 0):
            price_list = [o.price for o in self.orders]
            if self.orders:
                data_range = np.arange(min(price_list), max(price_list) + 1, self.tick_size)
            else:
                data_range = range(0,2,1)
            bids_dd = defaultdict(lambda x: 0)
            for row in data_range:
                bids_dd[row] = 0.00001
            for order in self.bids:
                bids_dd[order.price] += order.qty
            asks_dd = defaultdict(lambda x: 0)
            for row in data_range:
                asks_dd[row] = 0
            for order in self.asks:
                asks_dd[order.price] += order.qty
            data_dict = OrderedDict(
                [
                    ("Bids Qty", list(bids_dd.values())[::-1]), 
                    ("Price", list(data_range)[::-1]),
                    ("Asks Qty", list(asks_dd.values())[::-1])
                ]
            )
            data = pd.DataFrame(data_dict)
            data=data.to_dict('records')
            #columns=[{"name": i, "id": i} for i in data.columns]
            return data
        
        @dash_app.callback(
            Output("market_orders", "data"),
            Input('refresh_ui', 'n_intervals'))
        def display_table(mean = 0):

            self.trades.sort(key = lambda x: (x.o_time), reverse = True)
            data_dict = OrderedDict(
                [
                    ("Price", [t.price for t in self.trades]),
                    ("Qty", [t.qty for t in self.trades]),
                    ("Time", [datetime.datetime.fromtimestamp(t.o_time).strftime('%H:%M:%S.%f') for t in self.trades])
                ]
            )
            data = pd.DataFrame(data_dict)
            data=data.to_dict('records')
            #columns=[{"name": i, "id": i} for i in data.columns]
            return data

        @dash_app.callback(
            Output('container-button-basic-bid', 'children'),
            Input('bid-quote-val', 'n_clicks'),
            State('input-on-submit-bid', 'value')
        )
        def update_output_bid(n_clicks, value):
            if not value == None:
                price = math.floor(float(value)/self.tick_size)*self.tick_size
                print(f'Sending buy request at ${price}')
                sio.emit('BID', [price,1])
            else:
                price = None
            return 'Input "{}"'.format(
                price
            )
        @dash_app.callback(
            Output('container-button-basic-ask', 'children'),
            Input('ask-quote-val', 'n_clicks'),
            State('input-on-submit-ask', 'value')
        )
        def update_output_ask(n_clicks, value):
            if not value == None:
                price = math.ceil(float(value)/self.tick_size)*self.tick_size
                print(f'Sending ask request at ${price}')
                sio.emit('ASK', [price,1])
            else:
                price = None
            return 'Input "{}"'.format(
                price
            )

        @dash_app.callback(
            Output('settle_text', 'children'),
            Input('settle_btn', 'n_clicks')
        )
        def update_output_settle(n_clicks):
            if n_clicks < 5:
                return 'Are you sure?'
            else:
                sio.emit('settle', '23.5')
                return 'Settling'

        @dash_app.callback(Output('labelUI', 'children'),
            [Input('refresh_ui', 'n_intervals')])
        def update_interval(n):
            #sio.emit('BID', [200,3])
            return ''

        @dash_app.callback(Output('labelOB', 'children'),
            [Input('refresh_ob', 'n_intervals')])
        def update_interval(n):
            sio.emit('get_order_book', [])
            return ''

        port = 4000 + round(1000*random())
        dash_app.run_server(port=port, debug=True, use_reloader=False)


if __name__ == '__main__':
    print('launching server')
    start_server()
    cli = DashClient()
    cli.main()
   
