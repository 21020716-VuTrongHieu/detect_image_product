import os
import ssl
import gzip
import json
from io import BytesIO
from requests.adapters import HTTPAdapter
from urllib3.poolmanager import PoolManager
from dotenv import load_dotenv
import requests
load_dotenv()

class TLSAdapter(HTTPAdapter):
  """Adapter tùy chỉnh để hỗ trợ TLS v1.0 – v1.2"""
  def init_poolmanager(self, *args, **kwargs):
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.options |= ssl.OP_NO_TLSv1_3
    context.set_ciphers("DEFAULT:@SECLEVEL=1")
    kwargs['ssl_context'] = context
    return super().init_poolmanager(*args, **kwargs)

def get_bot_hostname():
  if os.getenv("DEV"):
    return "https://1344-2402-800-6d62-69ed-4c50-bef3-56ab-df7c.ngrok-free.app/api/v1"
  if os.getenv("STAGING"):
    return "https://staging.botcake.io/api/v1"
  return "https://botcake.io/api/v1"

def http_get(url, err_msg = "Không thể thực hiện GET", timeout = 45, headers=None, data=None, opts=None):
  headers = headers or {}
  data = data or {}
  opts = opts or {}
  if data:
    url = f"{url}?{requests.compat.urlencode(data)}"

  try:
    session = requests.Session()
    verify = not bool(os.getenv("DEV"))
    if verify:
      session.mount("https://", TLSAdapter())
      session.verify = "/etc/ssl/certs/ca-certificates.crt"
    else:
      session.verify = False

    response = session.get(url, headers=headers, timeout=timeout)
    return handle_http_response(response, url, err_msg, opts)
  except requests.RequestException as e:
    return {
      "success": False,
      "message": f"{err_msg}: {str(e)}",
    }

def http_post(url, data, err_msg = "Không thể thực hiện POST", headers=None, hackney_opts=None, opts=None):
  headers = headers or {}
  hackney_opts = hackney_opts or {}
  opts = opts or {}

  try:
    session = requests.Session()
    verify = not bool(os.getenv("DEV"))
    if verify:
      session.mount("https://", TLSAdapter())
      session.verify = "/etc/ssl/certs/ca-certificates.crt"
    else:
      session.verify = False

    response = session.post(url, data=data, headers=headers, timeout=45, **hackney_opts)
    return handle_http_response(response, url, err_msg, opts)
  except requests.RequestException as e:
    return {
      "success": False,
      "message": f"{err_msg}: {str(e)}",
    }

def http_post_json(url, data=None, err_msg = "Không thể thực hiện POST", headers=None, hackney_opts=None, opts=None):
  data = data or {}
  headers = headers or {}
  hackney_opts = hackney_opts or {}
  opts = opts or {}
  try:
    session = requests.Session()
    verify = not bool(os.getenv("DEV"))
    if verify:
      session.mount("https://", TLSAdapter())
      session.verify = "/etc/ssl/certs/ca-certificates.crt"
    else:
      session.verify = False
    
    headers["Content-Type"] = "application/json"
    response = session.post(url, data=json.dumps(data), headers=headers, timeout=45, **hackney_opts)
    return handle_http_response(response, url, err_msg, opts)
  except requests.RequestException as e:
    print(f"Error in http_post_json: {e}")
    return {
      "success": False,
      "message": f"{err_msg}: {str(e)}",
    }
  
def handle_http_response(response, url, err_msg, opts=None):
  opts = opts or {}
  if response is None:
    return {"success": False, "message": err_msg}
  
  try:
    status_code = response.status_code
    headers = response.headers
    is_gzipped = headers.get("Content-Encoding", "") in ["gzip", "x-gzip"]
    content = response.content
    if is_gzipped:
      with gzip.GzipFile(fileobj=BytesIO(content)) as f:
        content = f.read()
    
    try:
      decoded_body = json.loads(content)
    except json.JSONDecodeError:
      decoded_body = content.decode("utf-8", errors="replace")

    is_success = 200 <= status_code < 300
    result = {
      "success": is_success,
      "status_code": status_code,
      "response": decoded_body,
    }
    if opts.get("return_headers"):
      result["headers"] = dict(headers)

    return result
  except Exception as e:
    return {
      "success": False,
      "message": f"{err_msg}: {str(e)}",
    }