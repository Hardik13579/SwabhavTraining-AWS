import json
import base64
import boto3
import botocore
from boto3.dynamodb.conditions import Key, Attr
from decimal_encoder import DecimalEncoder



def lambda_handler(event, context):
    
    try:
        print(event)
    
        # method types
        get_method = "GET"
        post_method = "POST"
        delete_method = "DELETE"
        # resource types
        get_items_res = "/getalliproducts"
        order_res = "/orderitem"
        get_order_res = "/getordereditems"
        create_prod_res = "/createeditproduct"
        update_item_res = "/updateitem"
        delete_prod_res = "/deleteitem"
        
        method = event["requestContext"]["httpMethod"]
        resource = event["requestContext"]["resourcePath"]
        
        if method == get_method and resource == get_items_res:
            resp = get_items_list(event)
        elif method == post_method and resource == order_res:
            resp = order_item(event)
        elif method == post_method and resource == create_prod_res:
            resp = add_item(event)
        elif method == get_method and resource == get_order_res:
            resp = get_ordered_items(event)
        elif method == post_method and resource == update_item_res:
            resp = update_item(event)
        elif method == delete_method and resource == delete_prod_res:
            resp = delete_item(event)
        else:
            resp = "Unknown request."

        data = []
        error = {}
        output = {"Success": True,"Message":"Application Testing","data":resp, "error": error}
        
        return {
            'statusCode': 200,
            'isBase64Encoded': False,
            'body' : json.dumps(output, cls=DecimalEncoder),
            'headers': {
                'content-type': 'application/json',
                "Access-Control-Allow-Methods": 'OPTIONS,GET',
                "Access-Control-Allow-Origin": '*',
                "Access-Control-Allow-Header": 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'
            }
        }

    except botocore.exceptions.ClientError as e:
        data={}
        output={"Success": False,"Message":str(e.response['Error']['Message']),"data":data,"error":e.response['Error']['Code'] }
        return {
            'statusCode': 202,
            'isBase64Encoded': False,
            'body' : json.dumps(output, cls=DecimalEncoder),
            'headers': {
            'content-type': 'application/json',
            "Access-Control-Allow-Methods": 'OPTIONS,GET',
            "Access-Control-Allow-Origin": '*',
            "Access-Control-Allow-Header": 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'
            }
        }
        raise e
    
    
# DONE
def get_items_list(event):
    db = boto3.resource('dynamodb')
    table = db.Table('EkartItems')
    
    # tab types
    market = "market"
    published = "published"
    
    try:
        params = event["queryStringParameters"]
        email = params["email"]
        tab = params["tab"]
    except Exception as e:
        return "Missing query parameters"

    if tab == market:
        get_resp = table.scan(ScanFilter={'supplier_email':{'AttributeValueList': [email], 'ComparisonOperator': 'NE'}})
    elif tab == published:
        # query our email 
        get_resp = table.scan(ScanFilter={'supplier_email':{'AttributeValueList': [email], 'ComparisonOperator': 'EQ'}})
    
    items = get_resp['Items']
    print(items)

    return items


# DONE
def add_item(event):
    db = boto3.resource('dynamodb')
    table = db.Table('EkartItems')
    
    req_body = json.loads(event["body"])
    
    missing_field_error = { 'statusCode': 400, 'body': 'Missing field.' }
    try:
        prod_name = req_body["prod_name"]
        price = req_body["price"]
        quantity_available = req_body["quantity_available"]
        supplier_email = req_body["supplier_email"]
    except KeyError:
        return missing_field_error

    get_resp = table.scan(AttributesToGet=["item_id"])
    items = get_resp["Items"]
    print(get_resp)
    
    max_item_id = 0
    for item in items:
        print(item["item_id"])
        if int(item["item_id"]) > max_item_id:
            max_item_id = int(item["item_id"])
   
    item_id = max_item_id + 1
    Item = {
        "item_id": item_id, 
        "prod_name": prod_name, 
        "price": price, 
        "quantity_available": quantity_available, 
        "supplier_email": supplier_email
    }
    put_resp = table.put_item(Item=Item)
    
    print(put_resp)
    
    return Item
    
    
# DONE
def order_item(event):
    db = boto3.resource('dynamodb')
    items_table = db.Table('EkartItems')
    
    req_body = json.loads(event['body'])
    
    missing_field_error = { 'statusCode': 400, 'body': 'Missing field.' }
    item_doesnot_exist_error = { 'statusCode': 400, 'body': 'Item does not exist.' }
    try:
        email = req_body["email"]
        item_id = req_body["item_id"]
        order_status = req_body["order_status"]
        quantity = req_body["quantity"]
    except KeyError:
        return missing_field_error

    get_resp = items_table.get_item(Key={'item_id': item_id})
    if get_resp['Item'] == 0:
        return item_doesnot_exist_error
    item = get_resp['Item']
    print(item)
    
    if item['quantity_available'] < quantity:
        return "Ordered items more than available."
    
    cart_table = db.Table('EkartCart')
    item_in_cart_get_resp = cart_table.get_item(Key={'item_id': item_id, 'email': email})
    print(item_in_cart_get_resp)
    
    total_amount = item['price'] * quantity
    prod_name = item['prod_name']
    
    # For item already present in cart
    if "Item" in item_in_cart_get_resp:
        total_amount = total_amount + item_in_cart_get_resp['Item']['total_amount']
        total_quantity = item_in_cart_get_resp['Item']['quantity'] + quantity
        update_resp = cart_table.update_item(
            Key={
                'item_id': item_id,
                'email': email
            },
            UpdateExpression="set order_status = :o, prod_name = :p, quantity = :q, total_amount = :t",
            ExpressionAttributeValues={
                ':o': order_status,
                ':p': prod_name,
                ':q': total_quantity,
                ':t': total_amount
            })
        Item={
            'item_id': item_id, 
            'email': email,
            'order_status': order_status,
            'prod_name': prod_name, 
            'quantity': total_quantity, 
            'total_amount': total_amount
        }
        print("item exist and update", update_resp)
    else:
        Item={
            'item_id': item_id, 
            'email': email,
            'order_status': order_status,
            'prod_name': prod_name, 
            'quantity': quantity, 
            'total_amount': total_amount
        }
        put_resp = cart_table.put_item(Item=Item)
        print("put item", put_resp)

    return Item
    
    
# DONE
def get_ordered_items(event):
    db = boto3.resource('dynamodb')
    table = db.Table('EkartCart')
    
    try:
        params = event["queryStringParameters"]
        email = params["email"]
    except Exception as e:
        return "Missing query parameters."

    get_resp = table.scan(ScanFilter={'email':{'AttributeValueList': [email], 'ComparisonOperator': 'EQ'}, 'order_status':{'AttributeValueList': ['ordered'], 'ComparisonOperator': 'EQ'}})

    items = get_resp['Items']
    print(items)
    
    return items
    

# DONE
def update_item(event):
    db = boto3.resource('dynamodb')
    items_table = db.Table('EkartItems')
    
    req_body = json.loads(event['body'])
    
    missing_field_error = "Missing field."
    try:
        item_id = req_body["item_id"]
        prod_name = req_body["prod_name"]
        price = req_body["price"]
        quantity_available = req_body["quantity_available"]
        supplier_email = req_body["supplier_email"]
    except KeyError:
        return missing_field_error
        
    update_resp = items_table.update_item(
        Key={
            'item_id': item_id,
        },
        UpdateExpression="set price = :p, prod_name = :pn, quantity_available = :q, supplier_email = :s",
        ExpressionAttributeValues={
            ':p': price,
            ':pn': prod_name,
            ':q': quantity_available,
            ':s': supplier_email
        })
        
    return "Updated Item successfully"
    
    
#  DONE
def delete_item(event):
    print("delete the item")
    db = boto3.resource('dynamodb')
    table = db.Table('EkartItems')
    
    try:
        params = event["queryStringParameters"]
        email = params["email"]
        item_id = params["item_id"]
        print(item_id)
    except Exception as e:
        return "Missing query parameters"
        
    delete_resp = table.delete_item(Key={'item_id': int(item_id)})
    print(delete_resp)
    
    return "Item deleted successfully"