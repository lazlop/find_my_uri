import pickle                                                                                                                       
import json                                                                                                                         
import numpy as np                                                                                                                  
# Load the pickle files                                                                                                             
with open('find_my_uri/data/document_metadata.pickle', 'rb') as f:                                                                         
    metadata = pickle.load(f)

with open('find_my_uri/data/embeddings.pickle', 'rb') as f:                                                                                
    embeddings = pickle.load(f)                                                                                                    

embeddings_list = embeddings.tolist()                                                                                                              
with open('docs/data/metadata.json', 'w') as f:                                                                                     
    json.dump(metadata, f)                                                                                                          

with open('docs/data/embeddings.json', 'w') as f:                                                                                   
    json.dump(embeddings_list, f)                                                                                                   
print("Data converted to JSON successfully.")   