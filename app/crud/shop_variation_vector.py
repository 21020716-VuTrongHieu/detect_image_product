from sqlalchemy import text
from sqlalchemy.orm import Session

def find_similar_vectors(db: Session, vector, shop_id: int = None, limit: int = 10, threshold: float = 0.5):
  """
  Find similar vectors in the database.
  """
  filters = []
  if shop_id is not None:
    filters.append(f"shop_id = {shop_id}")

  # if threshold is not None:
  #   filters.append(f"vector <-> '{vector}' < {threshold}")

  where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""

  query = text(f"""
    SELECT shop_id, product_id, variation_id,
          vector <-> '{vector}' AS similarity
    FROM shop_variation_vector
    {where_clause}
    ORDER BY similarity
    LIMIT {limit};
  """)

  result = db.execute(query, {"vector": vector}).fetchall()
  return result
         