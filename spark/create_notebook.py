import nbformat as nbf
import json
import csv
import os

filenames = []
cypher_map ={}
model_maps = []
node_key_constraints = []
dataframes_data = {}

def spark_methods_block():
  spark_block = '''
import os
from pyspark.sql.types import StructType, StructField, StringType, IntegerType, FloatType, DoubleType, DateType, TimestampType
from pyspark import SparkConf, SparkContext
from pyspark.sql import SparkSession
from pyspark.conf import SparkConf
from pyspark.sql import SparkSession

config = {
    "user":"neo4j",
    "password":"password123",
    "url":"bolt://neodb:7687",
    "database":"autoneo",
    "batch_size":5000
}

spark = SparkSession \\
    .builder \\
    .appName("autoneo") \\
    .config("spark.jars", "./lib/neo4j-connector-apache-spark_2.12-4.1.2_for_spark_3.jar") \\
    .getOrCreate()

'''

  return spark_block

def create_db_with_constraints():
  create_db = f'''
!python3 -m pip install neo4j==5.9.0

from neo4j import GraphDatabase
import time

def get_driver():
  uri = "bolt://neodb:7687"
  return GraphDatabase.driver(uri, auth=("neo4j", "password123"))

def create_database(tx, dbname):
    tx.run("CREATE DATABASE $dbname", dbname=dbname)

driver = get_driver()
with driver.session(database="system") as session:
    try:
      session.execute_write(create_database, "autoneo")
      time.sleep(5)
    except Exception as e:
      print("Database already exists...")

with driver.session(database="autoneo") as session:
    {create_node_key_constraints()}

driver.close()

print("database 'autoneo' created and constraints set")
'''
  return create_db
  
def create_node_key_constraints():
  constraints = []
  for constraint in node_key_constraints:
    constraints.append(f"session.run('{constraint}')")
  return "\n    ".join(constraints)

def neo_methods_block():
  neo_block = '''
def write_neo4j_nodes(df, node_name):
    df.write \\
        .format("org.neo4j.spark.DataSource") \\
        .mode("Overwrite") \\
        .option("url", config["url"]) \\
        .option("batch.size", config["batch_size"]) \\
        .option("database", config["database"]) \\
        .option("authentication.type", "basic") \\
        .option("authentication.basic.username",  config["user"]) \\
        .option("authentication.basic.password", config["password"]) \\
        .option("query", get_cypher_query(node_name)) \\
        .save()

def write_neo4j_node_relationship(df, rel_map_key):
    df.write \\
        .format("org.neo4j.spark.DataSource") \\
        .mode("overwrite") \\
        .option("url", config["url"]) \\
        .option("batch.size", config["batch_size"]) \\
        .option("database", config["database"]) \\
        .option("authentication.type", "basic") \\
        .option("authentication.basic.username", config["user"]) \\
        .option("authentication.basic.password", config["password"]) \\
        .option("relationship", relationship_map[rel_map_key]["relationship"]["rel"]) \\
        .option("relationship.properties", relationship_map[rel_map_key]["relationship"]["properties"]) \\
        .option("relationship.save.strategy", "keys") \\
        .option("relationship.source.labels", relationship_map[rel_map_key]["source"]["node"]) \\
        .option("relationship.source.save.mode", "overwrite") \\
        .option("relationship.source.node.keys", relationship_map[rel_map_key]["source"]["property"]) \\
        .option("relationship.target.labels",  relationship_map[rel_map_key]["target"]["node"]) \\
        .option("relationship.target.node.keys", relationship_map[rel_map_key]["target"]["property"]) \\
        .option("relationship.target.save.mode", "overwrite") \\
    .save()
'''
  return neo_block

def lowercase_first_letter(str):
  return str[0].lower() + str[1:]

def create_dataframe_load_code():
  dataframes = []
  for file in os.listdir("./data/csv/"):
    filename = file.split(".csv")[0]
    filenames.append(filename)
    dataframes.append(f"{filename}_df = spark.read.option('header', True).csv('./data/csv/{filename}.csv')")
  return "\n".join(dataframes)
  
def create_nodes_code_block():
  code = []
  for item in list(cypher_map.keys()):
    dataframe = dataframes_data[item]
    code.append(f"write_neo4j_nodes({dataframe}_df, '{item}')")
  return "\n".join(code)

def create_relationships_code_block():
  code = []
  prev_model = ""
  for model_map in model_maps:
    for item in list(model_map.keys()):
      if not item == prev_model:
        dataframe = dataframes_data[item]
        code.append(f"write_neo4j_node_relationship({dataframe}_df, '{item}')")
      prev_model = item
  return "\n".join(code)

def create_notebook():
  notebook = nbf.v4.new_notebook()
  cells = []
  cell_group = []

  cells.append(nbf.v4.new_markdown_cell("### Main database and constraints"))
  cells.append(nbf.v4.new_code_cell(create_db_with_constraints()))
  cells.append(nbf.v4.new_markdown_cell("### Main config and methods for spark"))
  cells.append(nbf.v4.new_code_cell(spark_methods_block()))
  cells.append(nbf.v4.new_markdown_cell("### Load dataframes"))
  cells.append(nbf.v4.new_code_cell(create_dataframe_load_code()))
  cells.append(nbf.v4.new_markdown_cell("### Main cypher and config for nodes/relationships derived from data model"))
  cells.append(nbf.v4.new_code_cell(create_from_datamodel()))
  cells.append(nbf.v4.new_markdown_cell("### Node and relationship spark connector write methods for neo4j"))
  cells.append(nbf.v4.new_code_cell(neo_methods_block()))
  cells.append(nbf.v4.new_markdown_cell("### Write neo4j nodes"))
  cells.append(nbf.v4.new_code_cell(create_nodes_code_block()))
  cells.append(nbf.v4.new_markdown_cell("### Write neo4j relationships"))
  cells.append(nbf.v4.new_code_cell(create_relationships_code_block()))

  notebook["cells"] = cells
  with open("autoneo.ipynb", "w") as ipynb_file:
    nbf.write(notebook, ipynb_file)
    
def get_property_reference(value, type):
  if "|" in value:
      value = value.split("|")
      if type == "rel":
        value = value[1]
      else:
        value = value[0]
  
  value = value.split(".")[1]
  return value

def load_dataframes_data(value):
  if ":" in value:
    value_segs = value.split(":")
    if not value_segs[0] in dataframes_data:
      dataframes_data[value_segs[0]] = value_segs[1]
      
def create_from_datamodel():
  with open("./data/model/movies_datamodel.json") as f:
    datamodel = json.load(f)["dataModel"]
    nodes = datamodel["nodeLabels"]
    for item in nodes:
      label = nodes[item]["label"]
      props = nodes[item]["properties"]
      dataframe_data = nodes[item]["description"]
      load_dataframes_data(dataframe_data)
      constraints = []
      constraints_rel = []
      nonconstraints = []

      for prop in props:
        props_name = props[prop]["name"]
        columnname = get_property_reference(props[prop]["referenceData"], "node")

        if props[prop]["hasUniqueConstraint"]:
          columnname = get_property_reference(props[prop]["referenceData"], "node")
          columnname_rel = get_property_reference(props[prop]["referenceData"], "rel")
          constraints.append(f"{props_name}: event.{columnname}")
          constraints_rel.append(f"{columnname_rel}:{props_name}")
          if props[prop]["isPartOfKey"]:
            #CREATE CONSTRAINT IF NOT EXISTS FOR (n:Movie) REQUIRE (n.movieId) IS NODE KEY;
            node_key_constraints.append(f"CREATE CONSTRAINT IF NOT EXISTS FOR (n:{label}) REQUIRE (n.{props_name}) IS NODE KEY;")
        else:
          nonconstraints.append(f"n.{props_name} = event.{columnname}")

      nodes[item]["constraints_rel"] = constraints_rel
      constr_str = ", ".join(constraints)
      nonconst_str = ", ".join(nonconstraints)

      if not nonconst_str == "":
        nonconst_str = f" SET {nonconst_str}"

      merge_str = "MERGE (n:" + label + " {" + constr_str + "})" + nonconst_str
      cypher_map[lowercase_first_letter(label)] = merge_str
    
    cypher_map_method = f'''
def get_cypher_query(node_name):
  cypher_map = {json.dumps(cypher_map, indent=4)}
  return cypher_map[node_name.lower()]
'''
    #print(cypher_map_method)

    model_map = {}
    ## get relationships
    relationships = datamodel["relationshipTypes"]
    for rel in relationships:
      rel_props_lst = []
      type = relationships[rel]["type"]
      dataframe_data = relationships[rel]["description"]
      load_dataframes_data(dataframe_data)

      rel_props = relationships[rel]["properties"]
      src_node = relationships[rel]["startNodeLabelKey"]
      target_node = relationships[rel]["endNodeLabelKey"]
      src_node_label = nodes[src_node]["label"]
      target_node_label = nodes[target_node]["label"]
      
      for rel_prop in rel_props:
        prop_name = rel_props[rel_prop]["name"]
        value = get_property_reference(rel_props[rel_prop]["referenceData"], "rel")
        rel_props_lst.append(value)
      src_node_props = ", ".join(nodes[src_node]["constraints_rel"])
      target_node_props = ", ".join(nodes[target_node]["constraints_rel"])
      rel_props_str = ", ".join(rel_props_lst)

      model_map[f"{lowercase_first_letter(src_node_label)}_{lowercase_first_letter(target_node_label)}"] = { \
        "source": {"node": f":{src_node_label}", "property": src_node_props},
        "target": {"node": f":{target_node_label}", "property": target_node_props},
        "relationship": {"rel": type, "properties": rel_props_str}
      }
      model_maps.append(model_map)
    rel_map = f'''relationship_map = {json.dumps(model_map, indent=4)}'''

    return [rel_map, cypher_map_method]


create_from_datamodel()
create_db_with_constraints()

create_notebook()

print("\n")
print("***************************************************")
print("The autoneo notebook is created and ready to use...")
print("***************************************************")
print("\n")