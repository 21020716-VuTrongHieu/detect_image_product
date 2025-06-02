import os
import time
import pika
import threading
from app.workers.main_worker import assign_job
from dotenv import load_dotenv
load_dotenv()

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "guest")
RABBITMQ_PASSWORD = os.getenv("RABBITMQ_PASSWORD", "guest")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", 5672))
RABBITMQ_VHOST = os.getenv("RABBITMQ_VHOST", "/")
CONSUMING_QUEUE = os.getenv("CONSUMING_QUEUE", "task_pool")
PERFETCH_COUNT = int(os.getenv("PREFETCH_COUNT", 10))

RETRY_INTERVAL = 10

QUEUES = [
  "task_pool", "task_pool_error", "task_pool_retry_error"
]

ttl_queues = {
  **{f"wait_sec_{i:02d}": i * 1000 for i in range(1, 31)},
  **{f"wait_min_{i:02d}": i * 60000 for i in range(1, 31)}
}

class RabbitMQConsumer:
  def __init__(self):
    self.connection = None
    self.channel = None
    self.should_reconnect = False
    self._closing = False

  def connect(self):
    credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASSWORD)
    parameters = pika.ConnectionParameters(
      host=RABBITMQ_HOST,
      port=RABBITMQ_PORT,
      virtual_host=RABBITMQ_VHOST,
      credentials=credentials,
      heartbeat=600,
      blocked_connection_timeout=300,
      connection_attempts=3,
      frame_max=131072,
    )
    
    self.connection = pika.SelectConnection(
      parameters,
      on_open_callback=self.on_connection_open,
      on_close_callback=self.on_connection_closed,
      on_open_error_callback=self.on_connection_open_error,
      # stop_ioloop_on_close=False
    )

  def on_connection_open(self, connection):
    self.connection = connection
    self.connection.channel(on_open_callback=self.on_channel_open)
    print("✅ Connected to RabbitMQ successfully.")

  def on_connection_open_error(self, connection, error):
    print(f"Connection open failed: {error}")
    self.reconnect()

  def on_connection_closed(self, connection, reason):
    print(f"Connection closed: {reason}")
    self.channel = None
    self.connection = None
    if self._closing:
      print("Connection closed normally")
      self.connection.ioloop.stop()
    else:
      print(f"⚠️ Connection closed, reconnecting: {reason}")
      self.connection.ioloop.stop()
      self.reconnect()

  def reconnect(self):
    self.should_reconnect = True

  def on_channel_open(self, channel):
    self.channel = channel
    self.setup_queues()

  def setup_queues(self):
    self.channel.basic_qos(prefetch_count=PERFETCH_COUNT)

    for queue in ["task_pool", "task_pool_retry_error"]:
      self.channel.queue_declare(
        queue=queue,
        durable=True,
        arguments={
          "x-dead-letter-exchange": "",
          "x-dead-letter-routing-key": "task_pool_error"
        }
      )

    for queue in ["task_pool_error"]:
      self.channel.queue_declare(
        queue=queue,
        durable=True,
        arguments={
          "x-dead-letter-exchange": "",
          "x-dead-letter-routing-key": "task_pool",  #task_pool_retry_error
          "x-message-ttl": 60000
        }
      )

    for queue, ttl in ttl_queues.items():
      self.channel.queue_declare(
        queue=queue,
        durable=True,
        arguments={
          "x-dead-letter-exchange": "",
          "x-dead-letter-routing-key": "task_pool",
          "x-message-ttl": ttl
        }
      )

    self.start_consuming()

  def start_consuming(self):
    print(f"Listening on queue: {CONSUMING_QUEUE}")
    self.channel.basic_qos(prefetch_count=PERFETCH_COUNT)
    self.channel.basic_consume(
      queue=CONSUMING_QUEUE,
      on_message_callback=self.on_message,
      auto_ack=False
    )

  def on_message(self, ch, method, properties, body):
    assign_job(ch, method, body)

  def stop(self):
    self._closing = True
    if self.connection:
      self.connection.close()

  def run(self):
    while True:
      self.should_reconnect = False
      self._closing = False
      try:
        self.connect()
        self.connection.ioloop.start()
      except KeyboardInterrupt:
        print("Interrupted by user")
        self.stop()
        break
      except Exception as e:
        print(f"Error in RabbitMQ consumer: {e}")
      if self.should_reconnect:
        print("Reconnecting to RabbitMQ...")
        time.sleep(RETRY_INTERVAL)
      else:
        print("Consumer stopped.")
        break

def start_consumer():
  consumer = RabbitMQConsumer()
  thread = threading.Thread(target=consumer.run, daemon=True)
  thread.start()

if __name__ == "__main__":
  start_consumer()
  print("✅ RabbitMQ consumer started.")

    
