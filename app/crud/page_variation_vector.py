from sqlalchemy import text
from sqlalchemy.orm import Session

def find_similar_vectors(db: Session, vector, page_id: str = None, shop_id: str = None, limit: int = 10, threshold: float = 0.5):
  """
  Find similar vectors in the database.
  # """
  filters = []
  if page_id is not None:
    if shop_id:
      filters.append(f"(vd.page_shop_id = '{page_id}' OR vd.page_shop_id = '{shop_id}')")
    else:
      filters.append(f"vd.page_shop_id = '{page_id}'")
  if threshold is not None:
    filters.append(f"r.vector <=> '{vector}' < {threshold}")

  where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""
  query = text(f"""
    SELECT
      vd.page_shop_id,
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
    "limit": limit
  }).fetchall()
  return result


         