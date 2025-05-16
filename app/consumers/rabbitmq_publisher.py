# import pika
# import json
# import logging
# import threading

# RABBITMQ_HOST = "localhost"
# RABBITMQ_PORT = 5672
# RABBITMQ_VHOST = "/"
# RABBITMQ_USER = "guest"
# RABBITMQ_PASSWORD = "guest"

# class RabbitMQPublisher:
#   def __init__(self, queue, payload):
#     self.queue = queue
#     self.payload = payload
#     self.connection = None
#     self.channel = None

#   def connect(self):
#     credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASSWORD)
#     parameters = pika.ConnectionParameters(
#       host=RABBITMQ_HOST,
#       port=RABBITMQ_PORT,
#       virtual_host=RABBITMQ_VHOST,
#       credentials=credentials,
#       heartbeat=600,
#       blocked_connection_timeout=300,
#     )
    
#     self.connection = pika.SelectConnection(
#       parameters,
#       on_open_callback=self.on_connection_open,
#       on_close_callback=self.on_connection_closed,
#       # stop_ioloop_on_close=False
#     )

#   def on_connection_open(self, connection):
#     logging.info("Connected to RabbitMQ successfully.")
#     self.connection = connection
#     self.connection.channel(on_open_callback=self.on_channel_open)

#   def on_channel_open(self, channel):
#     logging.info("Channel opened.")
#     self.channel = channel
#     self.publish_message()

#   def publish_message(self):
#     try:
#       self.channel.basic_publish(
#         exchange="",
#         routing_key=self.queue,
#         body=json.dumps(self.payload),
#         properties=pika.BasicProperties(delivery_mode=2),
#       )
#     except Exception as e:
#       logging.error(f"Failed to enqueue message: {e}")
#     # finally:
#     #   self.connection.close()
#     #   logging.info("Connection closed.")

#   def on_connection_closed(self, connection, reason):
#     logging.warning(f"Connection closed: {reason}")

#   def run(self):
#     self.connect()
#     self.connection.ioloop.start()

# def enqueue(queue, payload):
#   publisher = RabbitMQPublisher(queue, payload)
#   thread = threading.Thread(target=publisher.run, daemon=True)
#   thread.start()

import os
import pika
import json
import logging
import threading

RABBITMQ_HOST = os.getenv("R_HOST", "localhost")
RABBITMQ_USER = os.getenv("R_USERNAME", "guest")
RABBITMQ_PASSWORD = os.getenv("R_PASSWORD", "guest")
RABBITMQ_PORT = int(os.getenv("R_PORT", 5672))
RABBITMQ_VHOST = os.getenv("R_VHOST", "/")


class RabbitMQPublisher:
  def __init__(self):
    self.connection = None
    self.channel = None
    self.lock = threading.Lock()

  def connect(self):
    credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASSWORD)
    parameters = pika.ConnectionParameters(
      host=RABBITMQ_HOST,
      port=RABBITMQ_PORT,
      virtual_host=RABBITMQ_VHOST,
      credentials=credentials,
      heartbeat=600,
      blocked_connection_timeout=300,
    )

    self.connection = pika.BlockingConnection(parameters)
    self.channel = self.connection.channel()
    logging.info("Connected to RabbitMQ successfully.")

  def publish_message(self, queue, payload):
    with self.lock:
      try:
        if not self.connection or self.connection.is_closed:
          logging.warning("Connection closed, reconnecting...")
          self.connect()

        self.channel.basic_publish(
          exchange="",
          routing_key=queue,
          body=json.dumps(payload),
          properties=pika.BasicProperties(delivery_mode=2),
        )
        logging.info(f"Message sent to {queue}")

      except Exception as e:
        logging.error(f"Failed to send message: {e}")
        self.connect() 

  def close(self):
    if self.connection and self.connection.is_open:
      self.connection.close()
      logging.info("RabbitMQ connection closed.")

rabbitmq_publisher = RabbitMQPublisher()

def enqueue(queue, payload):
  # message = json.dumps(payload)
  rabbitmq_publisher.publish_message(queue, payload)