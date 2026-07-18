import json
import os
import boto3
import urllib.request
import time
import logging

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
s3_client = boto3.client('s3')
bedrock_client = boto3.client('bedrock-runtime', region_name='us-east-1')
dynamodb = boto3.resource('dynamodb')

def transcribe_audio_with_groq(file_path):
    """Manually constructs a multipart/form-data request to Groq Whisper API using standard library."""
    groq_api_key = os.environ.get('GROQ_API_KEY')
    if not groq_api_key:
        raise ValueError("GROQ_API_KEY environment variable is missing.")

    logger.info("Starting Groq Whisper transcription...")
    
    boundary = '----WebKitFormBoundary7MA4YWxkTrZu0gW'
    body_parts = []
    
    # Add model field
    body_parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="model"\r\n\r\nwhisper-large-v3\r\n'.encode('utf-8'))
    
    # Add prompt field to force Roman Urdu (Minglish) output
    prompt_text = "This is a medical handover in Minglish (Roman Urdu and English). Please transcribe exactly as spoken using Roman English alphabets. For example: patient number 7 ka bp bohat high rehta hai usko subah check karna."
    body_parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="prompt"\r\n\r\n{prompt_text}\r\n'.encode('utf-8'))
    
    # Add file field
    body_parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="audio.webm"\r\nContent-Type: audio/webm\r\n\r\n'.encode('utf-8'))
    
    with open(file_path, 'rb') as f:
        body_parts.append(f.read())
        
    body_parts.append(f'\r\n--{boundary}--\r\n'.encode('utf-8'))
    payload = b''.join(body_parts)

    headers = {
        'Authorization': f'Bearer {groq_api_key}',
        'Content-Type': f'multipart/form-data; boundary={boundary}',
        'User-Agent': 'SBAR-Handover-App/1.0' # Required to bypass Cloudflare bot protection
    }
    
    req = urllib.request.Request('https://api.groq.com/openai/v1/audio/transcriptions', data=payload, headers=headers)
    
    try:
        response = urllib.request.urlopen(req, timeout=30)
        result = json.loads(response.read().decode('utf-8'))
        return result.get('text', '')
    except Exception as e:
        logger.error(f"Groq API Error: {str(e)}")
        raise

def generate_sbar_with_bedrock(transcript):
    """Sends the transcript to Amazon Nova Lite via Amazon Bedrock to extract SBAR JSON."""
    logger.info("Starting Bedrock SBAR extraction using Amazon Nova...")
    
    prompt = f"""You are a clinical AI assistant. You are given a transcript of a shift handover note which contains a mix of English and Urdu (in Arabic script).

First, read the transcript carefully. Pay special attention to Urdu grammar context (for example, "kal jana hai" means "needs to go TOMORROW", whereas "kal gaya tha" means "went YESTERDAY").

Then, convert this transcript into a structured SBAR format.
You must return ONLY a valid JSON object matching this schema without any other text:
{{
  "roman_minglish_transcript": "Rewrite the exact original transcript here, but convert ALL Urdu/Hindi script into Roman English alphabets (Minglish). Do not translate the Urdu words to English here, just transliterate them.",
  "situation": "brief statement of the problem",
  "background": "brief history and context",
  "assessment": "what you think the problem is",
  "recommendation": "what needs to be done",
  "patient_id": "extract patient ID or MR number if mentioned, else 'Unknown Patient'",
  "doctor_name": "extract doctor name if mentioned, else 'Unknown Doctor'"
}}

Transcript:
{transcript}"""

    try:
        # Using the modern Converse API which is much cleaner
        response = bedrock_client.converse(
            modelId="amazon.nova-lite-v1:0",
            messages=[
                {
                    "role": "user",
                    "content": [{"text": prompt}]
                }
            ],
            inferenceConfig={
                "maxTokens": 1000,
                "temperature": 0.1
            }
        )
        
        content = response['output']['message']['content'][0]['text'].strip()
        
        # Clean up in case the model adds markdown blocks
        if content.startswith('```json'):
            content = content[7:-3]
        elif content.startswith('```'):
            content = content[3:-3]
            
        start_idx = content.find('{')
        end_idx = content.rfind('}') + 1
        if start_idx != -1 and end_idx != -1:
            content = content[start_idx:end_idx]
            
        return json.loads(content)
    except Exception as e:
        logger.error(f"Bedrock API Error: {str(e)}")
        raise

def lambda_handler(event, context):
    logger.info(f"Received S3 Event: {json.dumps(event)}")
    
    try:
        # 1. Parse the S3 Event
        record = event['Records'][0]
        bucket_name = record['s3']['bucket']['name']
        object_key = record['s3']['object']['key']
        
        # The handover_id is the filename without extension
        # e.g., "audio/123-456.webm" -> "123-456"
        handover_id = object_key.split('/')[-1].split('.')[0]
        logger.info(f"Processing Handover ID: {handover_id}")
        
        # 2. Download audio to Lambda's temporary storage
        tmp_file_path = f"/tmp/{handover_id}.webm"
        s3_client.download_file(bucket_name, object_key, tmp_file_path)
        
        # 3. Transcribe audio using Groq Whisper
        transcript = transcribe_audio_with_groq(tmp_file_path)
        logger.info(f"Transcript: {transcript}")
        
        if not transcript:
            raise ValueError("Transcription returned empty text.")
            
        # 4. Generate SBAR JSON using Bedrock Claude 3
        sbar_data = generate_sbar_with_bedrock(transcript)
        logger.info("Successfully generated SBAR JSON")
        
        # 5. Save to DynamoDB
        table = dynamodb.Table('sbar-handovers')
        
        # We will extract the transliterated transcript from the LLM output
        minglish_transcript = sbar_data.pop('roman_minglish_transcript', transcript)
        
        item = {
            'handover_id': handover_id,
            'status': 'Complete',
            'created_at': int(time.time()),
            'raw_transcript': minglish_transcript, # This will now be pure Roman English alphabets
            **sbar_data
        }
        table.put_item(Item=item)
        
        logger.info("Successfully saved to DynamoDB")
        return {"statusCode": 200, "body": "Processing complete"}
        
    except Exception as e:
        logger.error(f"Pipeline failed: {str(e)}")
        
        # Fallback: Save failed status to DynamoDB if we got far enough to know the ID
        try:
            if 'handover_id' in locals():
                dynamodb.Table('sbar-handovers').put_item(Item={
                    'handover_id': handover_id,
                    'status': 'Failed',
                    'error_message': str(e),
                    'created_at': int(time.time())
                })
        except:
            pass
            
        raise e
