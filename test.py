import hashlib
import hmac
import json
import math
import time
import requests
url = "https://api.coinstore.com/api/v2/public/config/spot/symbols"
api_key='aa28a602437888abbddacd69444b1e8e'
secret_key = b'064c7016ed8cd6af2465b82705160c96'
expires = int(time.time() * 1000)
expires_key = str(math.floor(expires / 30000))
expires_key = expires_key.encode("utf-8")
key = hmac.new(secret_key, expires_key, hashlib.sha256).hexdigest()
key = key.encode("utf-8")
payload = json.dumps({
  "symbolCodes":["ETHUSDT"],
})
print(payload)
payload = payload.encode("utf-8")
signature = hmac.new(key, payload, hashlib.sha256).hexdigest()
headers = {
   'X-CS-APIKEY': api_key,
 'X-CS-SIGN': signature,
 'X-CS-EXPIRES': str(expires),
 'exch-language': 'en_US',
 'Content-Type': 'application/json',
 'Accept': '*/*',
 # 'Host': 'https://api.coinstore.com',
 'Connection': 'keep-alive'
}
print(headers)
print(payload)
response = requests.request("POST", url, headers=headers, data=payload)
print(response.text)