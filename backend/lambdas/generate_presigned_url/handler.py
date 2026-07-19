import json
import os
import boto3
import uuid
import logging
from botocore.exceptions import ClientError

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize the S3 client outside the handler for connection reuse
s3_client = boto3.client('s3')

def build_response(status_code, body):
    """Helper to format API Gateway responses with CORS headers."""
    return {
        'statusCode': status_code,
        'headers': {
            'Access-Control-Allow-Origin': '*', # In production, restrict to Amplify domain
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Allow-Methods': 'OPTIONS,GET,POST'
        },
        'body': json.dumps(body)
    }

def lambda_handler(event, context):
    logger.info("Received event: %s", json.dumps(event))
    
    bucket_name = os.environ.get('BUCKET_NAME')
    
    if not bucket_name:
        logger.error("BUCKET_NAME environment variable is not set")
        return build_response(500, {'error': 'Server misconfiguration'})
        
    try:
        # Generate a unique ID for this handover
        handover_id = str(uuid.uuid4())
        
        # Organize files by a prefix (e.g., audio/1234.webm)
        file_key = f"audio/{handover_id}.webm"
        
        # Generate the presigned URL
        presigned_url = s3_client.generate_presigned_url(
            ClientMethod='put_object',
            Params={
                'Bucket': bucket_name,
                'Key': file_key,
                'ContentType': 'audio/webm' # Ensures frontend uploads the correct format
            },
            ExpiresIn=300 # URL expires in 5 minutes
        )
        
        # --- NEW: Create a "Processing" record in DynamoDB ---
        import time
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table('sbar-handovers')
        table.put_item(Item={
            'handover_id': handover_id,
            'status': 'Processing',
            'created_at': int(time.time()),
            'patient_id': 'Processing Audio...',
            'situation': 'AI is analyzing the audio...',
            'background': '...',
            'assessment': '...',
            'recommendation': '...'
        })
        
        response_data = {
            'upload_url': presigned_url,
            'file_key': file_key,
            'handover_id': handover_id
        }
        
        logger.info("Successfully generated presigned URL for key: %s", file_key)
        return build_response(200, response_data)
        
    except ClientError as e:
        logger.error("Boto3 ClientError: %s", str(e))
        return build_response(500, {'error': 'Could not generate upload URL'})
    except Exception as e:
        logger.error("Unexpected error: %s", str(e))
        return build_response(500, {'error': 'Internal server error'})
