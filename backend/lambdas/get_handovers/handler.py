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
        
        # Handle CORS Preflight (OPTIONS)
        http_method = event.get('httpMethod', 'GET')
        if http_method == 'OPTIONS':
            return {
                'statusCode': 200,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Methods': 'OPTIONS,GET,DELETE,PUT',
                    'Access-Control-Allow-Headers': 'Content-Type,Authorization'
                },
                'body': ''
            }
            
        if http_method == 'DELETE':
            # Support both body payload and query string for ID
            body = json.loads(event.get('body', '{}'))
            handover_id = body.get('handover_id') or event.get('queryStringParameters', {}).get('handover_id')
            if handover_id:
                table.delete_item(Key={'handover_id': handover_id})
                return {
                    'statusCode': 200,
                    'headers': {'Access-Control-Allow-Origin': '*'},
                    'body': json.dumps({'message': 'Deleted successfully'})
                }
            return {
                'statusCode': 400,
                'headers': {'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'Missing handover_id'})
            }
            
        if http_method == 'PUT':
            body = json.loads(event.get('body', '{}'))
            handover_id = body.get('handover_id')
            if handover_id:
                # Update item fields
                update_expr = "set situation=:s, background=:b, assessment=:a, recommendation=:r, patient_id=:p, doctor_name=:d"
                table.update_item(
                    Key={'handover_id': handover_id},
                    UpdateExpression=update_expr,
                    ExpressionAttributeValues={
                        ':s': body.get('situation', ''),
                        ':b': body.get('background', ''),
                        ':a': body.get('assessment', ''),
                        ':r': body.get('recommendation', ''),
                        ':p': body.get('patient_id', ''),
                        ':d': body.get('doctor_name', '')
                    }
                )
                return {
                    'statusCode': 200,
                    'headers': {'Access-Control-Allow-Origin': '*'},
                    'body': json.dumps({'message': 'Updated successfully'})
                }
            return {
                'statusCode': 400,
                'headers': {'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'Missing handover_id'})
            }

        # Default: GET Request (Fetch all handovers)
        response = table.scan()
        items = response.get('Items', [])
        
        # Sort items by created_at (newest first)
        items.sort(key=lambda x: x.get('created_at', 0), reverse=True)

        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'OPTIONS,GET,DELETE,PUT',
                'Access-Control-Allow-Headers': 'Content-Type,Authorization'
            },
            'body': json.dumps({'handovers': items}, cls=DecimalEncoder)
        }
        
    except Exception as e:
        print(f"Error handling request: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({'error': str(e)})
        }
