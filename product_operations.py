import requests
from neo4j_connection import get_db_connection

API_KEY = "cldcav1hfppvdz5xegkaanmf2dgxom"
API_URL = "https://api.barcodelookup.com/v3/products"

def fetch_product_from_db(barcode):
    """Fetch product details from Neo4j database and convert it to a dictionary."""
    query = "MATCH (p:Product {barcode: $barcode})-[r]-(related) RETURN p,related"
    
    with get_db_connection() as driver:
        with driver.session() as session:
            result = session.run(query, barcode=barcode)
            records = result.data()
            
            if records:
                product_dict = {}
                
                for record in records:
                    product_node = record['p']
                    related_node = record['related']
                    
                    if 'p' not in product_dict:
                        product_dict['product'] = dict(product_node)
                    
                    if 'related_nodes' not in product_dict:
                        product_dict['related_nodes'] = []
                    product_dict['related_nodes'].append(dict(related_node))

                related_nodes = product_dict.get('related_nodes', [])
                for node in related_nodes:
                    if 'image' in node:
                        product_dict['product']['image'] = node['image']
                
                return product_dict

    return None


def add_product_to_db(product):
    """Add a new product to the Neo4j database."""
    barcode_number = product.get("barcode_number", None)
    title = product.get("title", None)
    category = product.get("category", None)
    brand = product.get("brand", None)
    manufacturer = product.get("manufacturer", None)
    image = product.get("image")

    query = """
    MERGE (p:Product {barcode: $barcode})
    ON CREATE SET p.title = $title

    MERGE (b:Brand {name: $brand})
    MERGE (c:Category {name: $category})
    MERGE (m:Manufacturer {name: $manufacturer})
    MERGE (i:Image {image: $image})

    MERGE (p)-[:BELONGS_TO]->(b)
    MERGE (p)-[:CLASSIFIED_AS]->(c)
    MERGE (p)-[:MANUFACTURED_BY]->(m)
    MERGE (p)-[:POSSESSES]->(i)
    """


    with get_db_connection() as driver:
        with driver.session() as session:
            session.run(query, barcode=barcode_number, title=title, category=category,
                brand=brand, manufacturer=manufacturer, image=image)
            print(f"Product {product['barcode_number']} added to Neo4j.")

def fetch_product(barcode):
    """Fetch product from Neo4j, if not found then fetch from API and add to Neo4j."""
    product = fetch_product_from_db(barcode)
    if product:
        print("Product found in Neo4j database.")
        return product
    
    print("Product not found in Neo4j. Fetching from API...")
    response = requests.get(API_URL, params={"barcode": barcode, "formatted": "y", "key": API_KEY})
    
    if response.status_code == 200:
        data = response.json()
        if "products" in data and data["products"]:
            product = data["products"][0]
            add_product_to_db(product)
            return product

    print("Product not found in API.")  
    return None

def fetch_all_products_from_neo4j():
    """Fetch all products from Neo4j."""
    query = """MATCH
        (p:Product)-[:CLASSIFIED_AS]->(c:Category),
        (p)-[:MANUFACTURED_BY]->(m:Manufacturer),
        (p)-[:BELONGS_TO]->(b:Brand) 
    OPTIONAL MATCH (p)-[:POSSESSES]->(i:Image)
    RETURN p.title as Title, c.name as Category, m.name as Manufacturer, b.name as Brand, COALESCE(i.name, '') AS Image"""

    with get_db_connection() as driver:
        with driver.session() as session:
            result = session.run(query)
            data = [record.data() for record in result]

    return data
