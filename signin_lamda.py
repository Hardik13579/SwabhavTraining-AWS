import json
import base64
import boto3
from boto3.dynamodb.conditions import Key, Attr

def lambda_handler(event, context):
    
    print(event)
    req_body = json.loads(event["body"])    
    
    missing_field_error = { 'statusCode': 400, 'body': 'Missing field.' }
    
    try:
        email = req_body["email"]
        pwd = req_body["pwd"]
    except KeyError:
        return missing_field_error
    
    return signin_user(email, pwd)



def signin_user(email, pwd):
    db = boto3.resource('dynamodb')
    table = db.Table('Users')
    
    # Validate user details for duplicate email
    get_resp = table.get_item(Key={'email': email})
    if not 'Item' in get_resp:
        return {
            'statusCode': 401,
            'body': json.dumps("Username or password incorrect.")
        }
        
    print(get_resp)
    user_details = get_resp['Item']
    
    # Encode password into base64 format
    encoded_pwd = base64.b64encode(pwd.encode("ascii"))
    
    if encoded_pwd != user_details['pwd']:
        return {
            'statusCode': 401,
            'body': json.dumps("Username or password incorrect.")
        }
    
    return {
        'statusCode': 200,
        'body': json.dumps('User sign-in successful.')
    }