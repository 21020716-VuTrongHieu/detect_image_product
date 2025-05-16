from sqlalchemy import text
from sqlalchemy.orm import Session

def find_similar_vectors(db: Session, vector, shop_id: int = None, limit: int = 10, threshold: float = 0.5):
  """
  Find similar vectors in the database.
  # """
  filters = []
  if shop_id is not None:
    filters.append(f"vd.shop_id = {shop_id}")
  if threshold is not None:
    filters.append(f"r.vector <=> '{vector}' < {threshold}")

  where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""
  query = text(f"""
    SELECT
      vd.shop_id,
      vd.product_id,
      vd.variation_id,
      vd.meta_data,
      r.vector <=> '{vector}' AS distance
    FROM variation_data vd
    JOIN variation_regions vr ON vd.id = vr.variation_data_id
    JOIN regions r ON vr.region_id = r.id
    {where_clause}
    ORDER BY distance ASC
    LIMIT :limit
  """)

  result = db.execute(query, {
    "vector": vector,
    "shop_id": shop_id,
    "threshold": threshold,
    "limit": limit
  }).fetchall()
  return result


         