import json

def prepare_paste_items(pastes):
    """ Prepare 'raw' list of Pastebin paste items for insert to DynamoDB table """
    
    new_pastes = []
    int_values = ['date', 'size']
    str_values = ['title', 'user', 'syntax']
    
    for paste in pastes:
        # make sure date values are int, not string
        for key in int_values:
            if key in paste:
                paste[key] = int(paste[key])
        
        # DynamoDB does not accept empty/null string values
        for key in str_values:         
            if key in paste and len(paste[key]) == 0:
                del paste[key]
        
        new_pastes.append(paste)
        
    return new_pastes