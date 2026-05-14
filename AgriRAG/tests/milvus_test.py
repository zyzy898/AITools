name1 = "big_model"
name2 = "xiaomi_car"


from pymilvus import MilvusClient,CollectionSchema,FieldSchema,DataType

client = MilvusClient(uri="http://10.253.205.160:19530")

schema = CollectionSchema([
    FieldSchema("id",DataType.INT64,is_primary=True),
    FieldSchema("text",DataType.VARCHAR,max_length=2000),
    FieldSchema("emb",DataType.FLOAT_VECTOR,dim=3)
])

index_params = client.prepare_index_params()
index_params.add_index(
    field_name="emb",
    metric_type="COSINE",
    index_type="",
    index_name="vector_index"
)
if client.has_collection(name1):
    client.drop_collection(name1)
if client.has_collection(name2):
    client.drop_collection(name2)

client.create_collection(collection_name=name1,schema=schema)
client.create_index(name1,index_params)

client.create_collection(collection_name=name2,schema=schema)
client.create_index(name2,index_params)


client.insert(name1,{"id":0,"text":'abc',"emb":[1,2,3]})
client.insert(name1,{"id":1,"text":'123',"emb":[12,21,30]})

client.insert(name2,{"id":0,"text":'abc',"emb":[1,2,3]})
client.insert(name2,{"id":1,"text":'123',"emb":[12,21,30]})

client.load_collection(name1)
client.load_collection(name2)

print(client.search(name1,[[12,3,4]],output_fields=["text"],limit=1))
print(client.search(name2,[[12,3,4]],output_fields=["text"],limit=1))


