

from dash import Dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, State
import socket
import sys

def main(type = 0):
    ClientSocket = socket.socket()
    host = socket.gethostname()
    port = 10016
    print('Waiting for connection')

    try:
        ClientSocket.connect((host, port))
        print('Connected')
    except socket.error as e:
        print(str(e))
    

    es = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
    app = Dash(__name__, external_stylesheets=es)
    
    bid_quote_input = [
        html.Div(dcc.Input(id='input-on-submit', type='text')),
        html.Button('Submit', id='bid-quote-val'),
        html.Div(id='container-button-basic',
                 children='Enter a value and press submit')
    ]
    app.layout = html.Div(bid_quote_input)
    
    @app.callback(
        Output('container-button-basic', 'children'),
        Input('bid-quote-val', 'n_clicks'),
        State('input-on-submit', 'value')
    )
    def update_output(n_clicks, value):
        if not value == None:
            print(f'Sending buy request at ${value}')
            ClientSocket.send(str.encode(str(value)))
            Response = ClientSocket.recv(1024)
            print(f"Response: {Response.decode('utf-8')}")
        return 'Input "{}"'.format(
            value
        )
    
    app.run_server(debug=True)
    #if type == 1: # sender
    #    while True:
    #        Input = input('Say Something: ')
    #        ClientSocket.send(str.encode(Input))
    #        Response = ClientSocket.recv(1024)
    #        print(f"Response: {Response.decode('utf-8')}")
    #else: # reciever
    #    while True:
    #        try:
    #            response = ClientSocket.recv(1024)
    #            print(f"Response: {response.decode('utf-8')}")
    #        except:
    #            pass


if __name__ == '__main__':
    main()
    #main(int(sys.argv[1]))
   