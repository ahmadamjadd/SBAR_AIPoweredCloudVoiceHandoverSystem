import json
import boto3
from decimal import Decimal

dynamodb = boto3.resource('dynamodb')

class DecimalEncoder(json.JSONEncoder):
    """DynamoDB returns numbers as Decimals. This converts them to ints/floats for standard JSON."""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return int(obj) if obj % 1 == 0 else float(obj)
        return super(DecimalEncoder, self).default(obj)

def lambda_handler(event, context):
    try:
        table = dynamodb.Table('sbar-handovers')
        
        # Scan the table (fetching all records). 
        # For a production app, we would use Query with an index, but Scan is fine for our prototype.
        response = table.scan()
        items = response.get('Items', [])
        
        # Sort items by created_at (newest first)
        items.sort(key=lambda x: x.get('created_at', 0), reverse=True)

        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*', # Adjust this to frontend domain in production
                'Access-Control-Allow-Methods': 'OPTIONS,GET',
                'Access-Control-Allow-Headers': 'Content-Type,Authorization'
            },
            'body': json.dumps({'handovers': items}, cls=DecimalEncoder)
        }
        
    except Exception as e:
        print(f"Error fetching handovers: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({'error': str(e)})
        }
