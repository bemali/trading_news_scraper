import os
from dotenv import load_dotenv
import http.client, urllib.parse

load_dotenv()

conn = http.client.HTTPSConnection('api.thenewsapi.com')

params = urllib.parse.urlencode({
    'api_token': os.getenv('news_api_key'),
    'categories': 'business,tech',
    'limit': 50,
    })

conn.request('GET', '/v1/news/all?{}'.format(params))

res = conn.getresponse()
data = res.read()

print(data.decode('utf-8'))