import json

def parse_json(path):
    '''
    'flatten' Sentiment json data so that each nested dictionary is one level.
    '''
    jsonString = None 
    with open(path, "r") as f:
        jsonString = f.read()
    
    j = json.loads(jsonString)
    flat_lists = []
    for nested_dict in j:
        temp_dict = {}
        temp_dict["color"] = nested_dict["color"]
        temp_dict["x"] = nested_dict["data"][0]["x"]
        temp_dict["y"] = nested_dict["data"][0]["y"]
        temp_dict["z"] = nested_dict["data"][0]["z"]
        temp_dict["name"] = nested_dict["data"][0]["name"]
        temp_dict["sentiment"] = nested_dict["data"][0]["sentiment"]
        flat_lists.append(temp_dict)
        

    with open('sentimentFixed.json', 'w') as outfile:
        json.dump(flat_lists, outfile)
    # return flat_lists


path = "sentiment.json"
parse_json(path)