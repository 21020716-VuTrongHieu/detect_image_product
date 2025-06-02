import os
from redis import Redis, ConnectionPool
from dotenv import load_dotenv
load_dotenv()

class RedisClient:
  _instance = None

  def __new__(cls):
    if cls._instance is None:
      cls._instance = super().__new__(cls)
      cls._instance._init_client()
    return cls._instance
  
  def _init_client(self):
    url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    self.pool = ConnectionPool.from_url(
      url,
      max_connections=int(os.getenv('REDIS_MAX_CONN', 50)),
      socket_timeout=float(os.getenv('REDIS_SOCKET_TIMEOUT', 5)),
      socket_connect_timeout=float(os.getenv('REDIS_CONNECT_TIMEOUT', 5)),
      decode_responses=True,
    )

    self.client = Redis(connection_pool=self.pool)
    self.client.ping()
    print("✅ Connected to Redis successfully.")

  def __getattr__(self, name):
    """
    Mọi attribute/method không tìm thấy trên RedisClient
    sẽ được lookup trên self.client
    """
    return getattr(self.client, name)

  # def command(self, *args, **kwargs):
  #   """
  #   Thực thi lệnh Redis đơn lẻ, ví dụ client.get('foo') tương đương
  #   command('GET', 'foo').
  #   """
  #   return self.client.execute_command(*args, **kwargs)
  
  # def pipeline(self, commands: List[Tuple]):
  #   """
  #   Thực thi batch các lệnh dạng pipeline.
  #   commands = [('SET', 'a', 1), ('INCR', 'counter')]
  #   """
  #   pipe = self.client.pipeline()
  #   for command in commands:
  #     pipe.execute_command(*command)
  #   return pipe.execute()