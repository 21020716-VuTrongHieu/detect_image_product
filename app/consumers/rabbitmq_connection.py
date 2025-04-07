import os
import time
import pika
import logging
import threading
from app.workers.main_worker import assign_job

RABBITMQ_HOST = os.getenv("R_HOST", "localhost")
RABBITMQ_USER = os.getenv("R_USERNAME", "guest")
RABBITMQ_PASSWORD = os.getenv("R_PASSWORD", "guest")
RABBITMQ_PORT = int(os.getenv("R_PORT", 5672))
RABBITMQ_VHOST = os.getenv("R_VHOST", "/")
CONSUMING_QUEUE = os.getenv("CONSUMING_QUEUE", "task_pool")
PERFETCH_COUNT = int(os.getenv("PREFETCH_COUNT", 10))

RETRY_INTERVAL = 10

QUEUES = [
  "task_pool", "task_pool_error", "task_pool_retry_error"
]

ttl_queues = {
  **{f"wait_sec_{i}": i * 1000 for i in range(1, 6)},
  **{f"wait_min_{i}": i * 60000 for i in range(1, 6)}
}

class RabbitMQConsumer:
  def __init__(self):
    self.connection = None
    self.channel = None
    self.should_reconnect = False
    self.connected = False

  def connect(self):
    logging.info("Connecting to RabbitMQ using SelectConnection...")
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
      # stop_ioloop_on_close=False
    )

  def on_connection_open(self, connection):
    logging.info("Connected to RabbitMQ successfully.")
    self.connected = True
    self.connection = connection
    self.connection.channel(on_open_callback=self.on_channel_open)

  def on_channel_open(self, channel):
    logging.info("Channel opened.")
    self.channel = channel
    self.setup_queues()

  def setup_queues(self):
    logging.info("Setting up queues...")

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
          "x-dead-letter-routing-key": "task_pool_retry_error",
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

    logging.info("Queues set up successfully.")
    self.start_consuming()

  def start_consuming(self):
    logging.info(f"Listening on queue: {CONSUMING_QUEUE}")
    self.channel.basic_qos(prefetch_count=PERFETCH_COUNT)
    self.channel.basic_consume(
      queue=CONSUMING_QUEUE,
      on_message_callback=self.on_message,
      auto_ack=False
    )

  def on_message(self, ch, method, properties, body):
    assign_job(ch, method, body)

  def on_connection_closed(self, connection, reason):
    logging.warning(f"Connection closed: {reason}")
    self.connected = False
    self.should_reconnect = True

  def run(self):
    while True:
      try:
        self.connect()
        self.connection.ioloop.start()
      except pika.exceptions.AMQPConnectionError as e:
        logging.error(f"Connection error: {e}. Retrying in {RETRY_INTERVAL} seconds...")
        time.sleep(RETRY_INTERVAL)

def start_consumer():
  consumer = RabbitMQConsumer()
  thread = threading.Thread(target=consumer.run, daemon=True)
  thread.start()

if __name__ == "__main__":
  start_consumer()
  logging.info("RabbitMQ setup completed.")

    
