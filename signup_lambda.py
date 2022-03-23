import json
import base64
import boto3
from boto3.dynamodb.conditions import Key, Attr

def lambda_handler(event, context):
    
    print(event)
    req_body = json.loads(event["body"])
    
    print(req_body)
    
    missing_field_error = { 'statusCode': 400, 'body': 'Missing field.' }
    
    try:
        email = req_body["email"]
        fname = req_body["fname"]
        lname = req_body["lname"]
        pwd = req_body["pwd"]
    except KeyError:
        return missing_field_error
    
    return signup_user(email, fname, lname, pwd)



def signup_user(email, fname, lname, pwd):
    db = boto3.resource('dynamodb')
    table = db.Table('Users')
    
    # Validate user details for duplicate email
    get_resp = table.get_item(Key={'email': email})
    print(get_resp)
    if 'Item' in get_resp:
        return {
            'statusCode': 400,
            'body': json.dumps("Please enter other email. Duplicate email error.")
        }
    
    # Encode password into base64 format
    encoded_pwd = base64.b64encode(pwd.encode("ascii"))

    # Insert user details into the table
    put_resp = table.put_item(Item={'email':email, 'fname': fname, 'lname': lname, 'pwd': encoded_pwd})
    
    return {
        'statusCode': 200,
        'body': json.dumps('User sign-up successful.')
    }