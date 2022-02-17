import datetime
import math
import sys
from collections import OrderedDict, defaultdict
from random import random

import jsonpickle
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import socketio
from dash import Dash, dash_table, dcc, html
from dash.dependencies import Input, Output, State
from flask import request

from typedefs_ob import Order, OrderBook, Settlement, Trade, Trader

# loop = asyncio.get_event_loop()
sio = socketio.Client()


def send_ping():
    sio.emit("ping_from_client")


@sio.event
def connect():
    print("connected to server")


@sio.on("*")
def catch_all(event, raw_data):
    if event == "sid":
        print(f"got sid: {raw_data}")
        cli.sid = raw_data
        return 0
    data = jsonpickle.decode(raw_data)
    if event == "insert":
        print(f"got insrt {data}")
        cli.handle_order(data)
    elif event == "cancel":
        print(f"got cancel {data}")
        cli.handle_cancel(data)
    elif event == "trade":
        print(f"got trade: {data}")
        cli.handle_trade(data)
    elif event == "order_book":
        print(f"got ob: {data}")
        cli.update_order_book(data)
    elif event == "settlement":
        print(f"got settlement")
        cli.print_settlement(data)
        sys.exit(0)
    pass

def start_server():
    sio.connect("http://localhost:5001")


class DashClient:
    def __init__(self) -> None:
        self.order_book = OrderBook(
            bids=[], asks=[], orders=[], trades=[], traders=[], tick_size=None
        )
        #self.orders = []
        #self.order_book_df = pd.DataFrame()
        #self.bids = []
        #self.bid_px_q = []
        #self.asks = []
        #self.ask_px_q = []
        #self.tick_size = 1
        #self.trades = []
        self.bidorderlist = []
        self.askorderlist = []
        self.full_levels = []
        self.mytrades = []
        self.sid = ""
        sio.emit("get_order_book", [])
        sio.emit("get_sid", [])

        print("init")

    def handle_order(self, order):
        self.order_book.orders.append(order)
        if order.o_type == "BID":
            self.order_book.bids.append(order)
        elif order.o_type == "ASK":
            self.order_book.asks.append(order)
        return 0

    def handle_cancel(self, order):
        print(order)
        print(self.order_book.orders)
        self.order_book.orders = [o for o in self.order_book.orders if not o.o_time == order.o_time]
        if order.o_type == "BID":
            self.order_book.bids = [o for o in self.order_book.bids if not o.o_time == order.o_time]
        elif order.o_type == "ASK":
            self.order_book.asks = [o for o in self.order_book.asks if not o.o_time == order.o_time]
        print("removed order")
        return 0

    def print_settlement(self, settlement):
        print(f'Own sid: {self.sid}')
        for trade_str in settlement.trades_text:
            print(trade_str)
        print(f"total pnl: {settlement.pnl}")
        sio.disconnect()

    def update_order_book(self, order_book):
        self.order_book = order_book
        return 0

    def handle_trade(self, trade):
        if trade.resting_order not in [t.id for t in self.order_book.orders]:
            print("Oops, we dont have a copy of the resting order")
            raise IndexError
        self.order_book.trades.append(trade)
        if self.sid in [trade.bid_sid, trade.ask_sid]:
            self.mytrades.append(trade)
        self.order_book.orders = [
            order for order in self.order_book.orders if order.id != trade.resting_order
        ]
        if trade.resting_order_type == "BID":
            self.order_book.bids = [
                order for order in self.order_book.bids if order.id != trade.resting_order
            ]
        elif trade.resting_order_type == "ASK":
            self.order_book.asks = [
                order for order in self.order_book.asks if order.id != trade.resting_order
            ]
        return 0

    def cancel_trades(self, price):
        sio.emit("cancel", str(price))
        return 0

    def main(self):
        print("launching dash")
        es = ["https://codepen.io/chriddyp/pen/bWLwgP.css"]
        dash_app = Dash(__name__, external_stylesheets=es)
        bid_quote_input = [
            html.Div(dcc.Input(id="input-on-submit-bid", type="text")),
            html.Button("Submit Bid", id="bid-quote-val"),
            html.Div(
                id="container-button-basic-bid",
                children="Enter a bid and press submit"
            ),
        ]
        ask_quote_input = [
            html.Div(dcc.Input(id="input-on-submit-ask", type="text")),
            html.Button("Submit Ask", id="ask-quote-val"),
            html.Div(
                id="container-button-basic-ask",
                children="Enter an offer and press submit",
            ),
        ]
        settle_input = [
            html.Button("SETTLE", id="settle_btn", n_clicks=0),
            html.Div(id="settle_text", children=""),
        ]

        data_dict = OrderedDict(
            [
                ("Bids Qty", []),
                ("Price", []),
                ("Asks Qty", []),
            ]
        )
        data = pd.DataFrame(data_dict)

        o_data_dict = OrderedDict(
            [
                ("Price", []),
                ("Qty", []),
                ("Time", []),
            ]
        )
        o_data = pd.DataFrame(o_data_dict)

        dash_app.layout = html.Div(
            children=[
                html.Div(
                    [
                        dcc.Interval(id="refresh_ui", interval=2500, n_intervals=0),
                        html.H1(id="labelUI", children=""),
                        html.H1(id="labelUG", children=""),
                    ]
                ),
                html.Div(
                    [
                        dcc.Interval(id="refresh_ob", interval=15000, n_intervals=0),
                        html.H1(id="labelOB", children=""),
                    ]
                ),
                html.H1(children="Mock Exchange", style={"textAlign": "center"}),
                html.Div(
                    dcc.Graph(id="graph"),
                    style={
                        "width": "49%",
                        "display": "inline-block",
                        "vertical-align": "top",
                    },
                ),
                html.Div(
                    [
                        html.Label("Market Orders", style={"textAlign": "center"}),
                        html.Div(
                            dash_table.DataTable(
                                id="market_orders",
                                style_data={
                                    "width": "10px",
                                },
                                columns=[{"name": i, "id": i} for i in data.columns],
                                style_cell_conditional=[
                                    {"if": {"column_id": "Bids Qty"}, "width": "130px"},
                                    {
                                        "if": {"column_id": "Bids Qty"},
                                        "textAlign": "right",
                                    },
                                    {
                                        "if": {"column_id": "Price"},
                                        "textAlign": "center",
                                    },
                                    {"if": {"column_id": "Price"}, "width": "50px"},
                                    {"if": {"column_id": "Asks Qty"}, "width": "130px"},
                                ],
                                data=data.to_dict("records"),
                                style_cell=dict(textAlign="left", fontSize=20),
                                style_header=dict(backgroundColor="paleturquoise"),
                            ),
                            style={"margin": "auto"},
                        ),
                    ],
                    style={
                        "width": "20%",
                        "display": "inline-block",
                        "vertical-align": "top",
                        "margin": "auto",
                        "padding": "10px",
                    },
                ),
                html.Div(
                    [
                        html.Label(
                            "My Orders (Click to cancel)", style={"textAlign": "center"}
                        ),
                        html.Div(
                            dash_table.DataTable(
                                id="my_orders",
                                style_data={
                                    "width": "10px",
                                },
                                columns=[{"name": i, "id": i} for i in data.columns],
                                style_cell_conditional=[
                                    {"if": {"column_id": "Bids Qty"}, "width": "130px"},
                                    {
                                        "if": {"column_id": "Bids Qty"},
                                        "textAlign": "right",
                                    },
                                    {
                                        "if": {"column_id": "Price"},
                                        "textAlign": "center",
                                    },
                                    {"if": {"column_id": "Price"}, "width": "50px"},
                                    {"if": {"column_id": "Asks Qty"}, "width": "130px"},
                                ],
                                data=data.to_dict("records"),
                                style_cell=dict(textAlign="left", fontSize=20),
                                style_header=dict(backgroundColor="paleturquoise"),
                            ),
                            style={"margin": "auto"},
                        ),
                    ],
                    style={
                        "width": "20%",
                        "display": "inline-block",
                        "vertical-align": "top",
                        "margin": "auto",
                        "padding": "10px",
                    },
                ),
                html.Div(bid_quote_input + ask_quote_input + settle_input),
                html.Div(
                    [
                        html.Label("Market Trades", style={"textAlign": "center"}),
                        dash_table.DataTable(
                            id="market_trades",
                            data=o_data.to_dict("records"),
                            columns=[{"id": c, "name": c} for c in o_data.columns],
                            style_cell=dict(textAlign="left", fontSize=15),
                            page_action="none",
                            style_table={"height": "300px", "overflowY": "auto"},
                        ),
                    ],
                    style={
                        "width": "49%",
                        "display": "inline-block",
                        "vertical-align": "top",
                        "padding": "10px",
                    },
                ),
                html.Div(
                    [
                        html.Label("My Trades", style={"textAlign": "center"}),
                        dash_table.DataTable(
                            id="my_trades",
                            data=o_data.to_dict("records"),
                            columns=[{"id": c, "name": c} for c in o_data.columns],
                            style_cell=dict(textAlign="left", fontSize=15),
                            page_action="none",
                            style_table={"height": "300px", "overflowY": "auto"},
                        ),
                    ],
                    style={
                        "width": "49%",
                        "display": "inline-block",
                        "vertical-align": "top",
                        "padding": "10px",
                    },
                ),
            ]
        )

        @dash_app.callback(
            Output("graph", "figure"), Input("refresh_ui", "n_intervals")
        )
        def display_color(mean=0):
            price_list = [o.price for o in self.orders]
            if self.order_book.orders:
                data_range = np.arange(
                    min(price_list), max(price_list) + 1, self.order_book.tick_size
                )
            else:
                data_range = range(0, 2, 1)

            bids_dd = defaultdict(lambda: 0)
            for row in data_range:
                bids_dd[row] = 0
            for order in self.bids:
                bids_dd[order.price] += order.qty

            asks_dd = defaultdict(lambda: 0)
            for row in data_range:
                asks_dd[row] = 0
            for order in self.asks:
                asks_dd[order.price] += order.qty

            fig = go.Figure(layout={"title": "Market Orders"})
            fig_b = go.Bar(
                x=list(data_range),
                y=list(bids_dd.values()),
                width=[self.order_book.tick_size for i in data_range],
            )
            fig_a = go.Bar(
                x=list(data_range),
                y=list(asks_dd.values()),
                width=[self.order_book.tick_size for i in data_range],
            )

            fig.add_trace(fig_a)
            fig.add_trace(fig_b)

            fig.update_layout(barmode="overlay")
            return fig

        @dash_app.callback(
            Output("market_orders", "data"), Input("refresh_ui", "n_intervals")
        )
        def display_table(mean=0):
            self.order_book.bids.sort(key=lambda x: (x.price), reverse=True)
            self.order_book.asks.sort(key=lambda x: (x.price))

            bids_dd = defaultdict(lambda: 0)
            for order in self.order_book.bids:
                bids_dd[order.price] += order.qty
            asks_dd = defaultdict(lambda: 0)
            for order in self.order_book.asks:
                asks_dd[order.price] += order.qty
            full_levels = list(asks_dd.keys())[::-1] + list(bids_dd.keys())
            bid_list = [bids_dd[k] if k in bids_dd else 0 for k in full_levels]
            ask_list = [asks_dd[k] if k in asks_dd else 0 for k in full_levels]
            data_dict = OrderedDict(
                [("Bids Qty", bid_list), ("Price", full_levels), ("Asks Qty", ask_list)]
            )
            data = pd.DataFrame(data_dict)
            data = data.to_dict("records")
            return data

        @dash_app.callback(
            Output("my_orders", "data"), Input("refresh_ui", "n_intervals")
        )
        def display_table(mean=0):
            self.order_book.bids.sort(key=lambda x: (x.price), reverse=True)
            self.order_book.asks.sort(key=lambda x: (x.price))

            bids_dd = defaultdict(lambda: 0)
            self_bids_dd = defaultdict(lambda: 0)
            for order in self.order_book.bids:
                bids_dd[order.price] += order.qty
                if order.sid == self.sid:
                    self_bids_dd[order.price] += order.qty
            asks_dd = defaultdict(lambda: 0)
            self_asks_dd = defaultdict(lambda: 0)
            for order in self.order_book.asks:
                asks_dd[order.price] += order.qty
                if order.sid == self.sid:
                    self_asks_dd[order.price] += order.qty

            full_levels = list(asks_dd.keys())[::-1] + list(bids_dd.keys())
            bid_list = [
                self_bids_dd[k] if k in self_bids_dd else 0 for k in full_levels
            ]
            ask_list = [
                self_asks_dd[k] if k in self_asks_dd else 0 for k in full_levels
            ]
            self.bidorderlist = bid_list
            self.askorderlist = ask_list
            self.full_levels = full_levels
            data_dict = OrderedDict(
                [("Bids Qty", bid_list), ("Price", full_levels), ("Asks Qty", ask_list)]
            )
            data = pd.DataFrame(data_dict)
            data = data.to_dict("records")
            # columns=[{"name": i, "id": i} for i in data.columns]
            return data

        @dash_app.callback(
            Output("market_trades", "data"), Input("refresh_ui", "n_intervals")
        )
        def display_table(mean=0):

            self.order_book.trades.sort(key=lambda x: (x.o_time), reverse=True)
            data_dict = OrderedDict(
                [
                    ("Price", [t.price for t in self.order_book.trades]),
                    ("Qty", [t.qty for t in self.order_book.trades]),
                    (
                        "Time",
                        [
                            datetime.datetime.fromtimestamp(t.o_time).strftime(
                                "%H:%M:%S.%f"
                            )
                            for t in self.order_book.trades
                        ],
                    ),
                ]
            )
            data = pd.DataFrame(data_dict)
            data = data.to_dict("records")
            # columns=[{"name": i, "id": i} for i in data.columns]
            return data

        @dash_app.callback(
            Output("my_trades", "data"), Input("refresh_ui", "n_intervals")
        )
        def display_table(mean=0):
            self.order_book.mytrades.sort(key=lambda x: (x.o_time), reverse=True)
            data_dict = OrderedDict(
                [
                    ("Price", [t.price for t in self.order_book.mytrades]),
                    ("Qty", [t.qty for t in self.order_book.mytrades]),
                    (
                        "Time",
                        [
                            datetime.datetime.fromtimestamp(t.o_time).strftime(
                                "%H:%M:%S.%f"
                            )
                            for t in self.order_book.mytrades
                        ],
                    ),
                ]
            )
            data = pd.DataFrame(data_dict)
            data = data.to_dict("records")
            # columns=[{"name": i, "id": i} for i in data.columns]
            return data

        @dash_app.callback(
            Output("container-button-basic-bid", "children"),
            Input("bid-quote-val", "n_clicks"),
            State("input-on-submit-bid", "value"),
        )
        def update_output_bid(n_clicks, value):
            if not value == None:
                price = math.floor(float(value) / self.order_book.tick_size) * self.order_book.tick_size
                sio.emit("BID", [price, 1])
            else:
                price = None
            return 'Input "{}"'.format(price)

        @dash_app.callback(
            Output("container-button-basic-ask", "children"),
            Input("ask-quote-val", "n_clicks"),
            State("input-on-submit-ask", "value"),
        )
        def update_output_ask(n_clicks, value):
            if not value == None:
                price = math.ceil(float(value) / self.order_book.tick_size) * self.order_book.tick_size
                sio.emit("ASK", [price, 1])
            else:
                price = None
            return 'Input "{}"'.format(price)

        @dash_app.callback(
            Output("settle_text", "children"), Input("settle_btn", "n_clicks")
        )
        def update_output_settle(n_clicks):
            if n_clicks == 1:
                return "Are you sure? Click again to confirm."
            if n_clicks == 2:
                sio.emit("settle", "23.5")
                return "Settling"

        @dash_app.callback(
            Output("labelUI", "children"), [Input("refresh_ui", "n_intervals")]
        )
        def update_interval(n):
            # sio.emit('BID', [200,3])
            return ""

        @dash_app.callback(
            Output("labelOB", "children"), [Input("refresh_ob", "n_intervals")]
        )
        def update_interval(n):
            sio.emit("get_order_book", [])
            return ""

        @dash_app.callback(
            Output("labelUG", "children"), Input("my_orders", "active_cell")
        )
        def update_graphs(active_cell):
            if active_cell:
                price = self.full_levels[active_cell["row"]]
                if active_cell["column"] == 0:
                    if not self.bidorderlist[active_cell["row"]] == 0:
                        self.cancel_trades(price)
                elif active_cell["column"] == 2:
                    if not self.bidorderlist[active_cell["row"]] == 0:
                        self.cancel_trades(price)
            return ""

        port = 4000 + round(1000 * random())
        dash_app.run_server(port=port, debug=True, use_reloader=False)


if __name__ == "__main__":
    start_server()
    cli = DashClient()
    cli.main()
