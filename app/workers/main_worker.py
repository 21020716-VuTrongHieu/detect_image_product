import json
import uuid
import logging
from datetime import datetime
from app.workers import variation_worker, user_worker

def assign_job(chan, tag, payload):
  task_id = str(uuid.uuid4())
  timestamp = datetime.now().isoformat()

  try:
    obj = json.loads(payload)
    payload = obj.get("payload", {})
    
    match obj.get("action"):
      case "test":
        user_worker.test(payload)
      case "upload":
        variation_worker.upload(payload)
      case "statistic_upload":
        variation_worker.statistic_upload(payload)
      case "update_status_callback":
        variation_worker.update_status_callback(payload)
      case _:
        logging.warning(f"Unknown action: {obj['action']}")

    chan.basic_ack(delivery_tag=tag.delivery_tag)
  except json.JSONDecodeError as e:
    logging.error(f"Failed to decode JSON: {e}")
    chan.basic_ack(delivery_tag=tag.delivery_tag)
  except Exception as e:
    logging.error(f"An error occurred: {e}")
    chan.basic_nack(delivery_tag=tag.delivery_tag, requeue=False)


      
    
