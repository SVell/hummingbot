import websocket
import json
import threading
import ssl
import time
import _thread
import math
import hmac
import hashlib

# WebSocket URL
url_ws = 'wss://ws.coinstore.com/s/ws'

# Enum for all possible subscription channel types
wssPaths = {
    'spot_asset': 'spot_asset',
    'spot_order': 'spot_order',
    'ticker': '623@ticker',
    'snapshot_depth': '623@snapshot_depth@20@0.00000000001',
    'kline': '623@kline@hour_12'
}
# Function to dynamically generate the signature
def get_sign(apikey, secretkey):
    expires = int(time.time() * 1000)  # Get current timestamp
    expires_key = str(math.floor(expires / 30000)).encode('utf-8')  # Format timestamp as key
    secretkey = secretkey.encode('utf-8')

    # Generate HMAC SHA256 signature
    newsecret_key = hmac.new(secretkey, expires_key, digestmod=hashlib.sha256).hexdigest()
    payload = str(expires).encode('utf-8')
    signature = hmac.new(newsecret_key.encode('utf-8'), payload, digestmod=hashlib.sha256).hexdigest()

    return str(expires), signature


# Send the API Key authentication request
def send_auth_apiKey(ws, apikey, secretkey, channel):
    expires, signature = get_sign(apikey, secretkey)  # Dynamically generate signature and timestamp
    auth = {
        "op": "login",
        "channel": [channel],
        "auth": {
            "token": apikey,
            "type": "apikey",
            "expires": expires,
            "signature": signature
        },
        "params": {}
    }
    ws.send(json.dumps(auth))


# Subscription request
def subscribe_channel(ws, channel):
    sub_msg = {
        "op": "SUB",
        "channel": [channel],
        "id": 1
    }
    ws.send(json.dumps(sub_msg))


# Send pong messages to keep the connection alive
def send_pong(ws):
    while True:
        epochMillis = int(time.time() * 1000)
        pong_message = {
            "op": "pong",
            "epochMillis": epochMillis
        }
        ws.send(json.dumps(pong_message))
        time.sleep(5)  # Send pong every 5 seconds


# Handle messages received from the WebSocket
def on_message(ws, message):
    print("Received message: %s" % message)


# Handle errors encountered in the WebSocket connection
def on_error(ws, error):
    print(error)


# Handle WebSocket connection closure
def on_close(ws, close_status_code, close_msg):
    print("### Connection closed ###")


# Handle WebSocket connection opening
def on_open(ws, apikey, secretkey, channels):
    def run(*args):
        # Send authentication request
        for channel in channels:
            send_auth_apiKey(ws, apikey, secretkey,
                             wssPaths[channel])  # Authenticate and subscribe to the specified channel

        time.sleep(1)

        # Subscribe to other specified channels
        for channel in channels:
            subscribe_channel(ws, wssPaths[channel])  # Subscribe to channels

        # Start the heartbeat mechanism to keep the connection alive
        send_pong(ws)

    _thread.start_new_thread(run, ())


# WebSocket thread class
class myThread(threading.Thread):
    def __init__(self, ws_url, apikey, secretkey, channels, header=None):
        super().__init__()
        self.url = ws_url
        self.apikey = apikey
        self.secretkey = secretkey
        self.channels = channels
        self.header = header

    def run(self):
        websocket.enableTrace(False)
        ws = websocket.WebSocketApp(self.url, on_message=on_message, on_error=on_error, on_close=on_close,
                                    header=self.header)
        ws.on_open = lambda ws: on_open(ws, self.apikey, self.secretkey, self.channels)
        ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})


# Set your API Key and Secret Key
api_key='aa28a602437888abbddacd69444b1e8e'
secret_key = '064c7016ed8cd6af2465b82705160c96'
channels_to_subscribe = ['spot_asset']  # Choose which channels to subscribe to

# Create and start the WebSocket thread
ws_thread = myThread(url_ws, api_key, secret_key, channels_to_subscribe)
ws_thread.start()