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
    """Transcribes audio using Groq Whisper while preserving medical wording."""

    groq_api_key = os.environ.get("GROQ_API_KEY")
    if not groq_api_key:
        raise ValueError("GROQ_API_KEY environment variable is missing.")

    logger.info("Starting Groq Whisper transcription...")

    boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
    body_parts = []

    fields = {
        "model": "whisper-large-v3",
        "temperature": "0",
        "response_format": "json",
        "prompt": """
This is a hospital doctor-to-doctor shift handover from Pakistan.

The speaker may switch between:
- English
- Urdu
- Roman Urdu

Rules:
- Produce a VERBATIM transcript.
- Never summarize.
- Preserve all numbers exactly.
- Preserve patient IDs exactly.
- Preserve bed numbers exactly.
- Preserve medicine names exactly.
- Preserve laboratory values exactly.
- Preserve doctor names exactly.
- Preserve medical abbreviations exactly.
"""
    }

    for key, value in fields.items():
        body_parts.append(
            f'--{boundary}\r\n'
            f'Content-Disposition: form-data; name="{key}"\r\n\r\n'
            f'{value}\r\n'.encode()
        )

    body_parts.append(
        f'--{boundary}\r\n'
        f'Content-Disposition: form-data; name="file"; filename="audio.webm"\r\n'
        f'Content-Type: audio/webm\r\n\r\n'.encode()
    )

    with open(file_path, "rb") as f:
        body_parts.append(f.read())

    body_parts.append(f"\r\n--{boundary}--\r\n".encode())

    payload = b"".join(body_parts)

    headers = {
        "Authorization": f"Bearer {groq_api_key}",
        "Content-Type": f"multipart/form-data; boundary={boundary}",
        "User-Agent": "SBAR-Handover-App/1.0"
    }

    req = urllib.request.Request(
        "https://api.groq.com/openai/v1/audio/transcriptions",
        data=payload,
        headers=headers
    )

    response = urllib.request.urlopen(req, timeout=60)

    result = json.loads(response.read().decode())

    return result.get("text", "")

def generate_sbar_with_bedrock(transcript):

    logger.info("Starting Clinical Extraction...")

    extraction_prompt = f"""
ROLE
You are an AI clinical information extraction system.

OBJECTIVE
Extract ONLY information explicitly stated in the transcript.

Never diagnose.
Never infer.
Never assume.
Never guess.

If information is not explicitly mentioned,
return "Unknown".

Preserve:
- numbers
- IDs
- medicine names
- laboratory values
- doctor names

Return ONLY valid JSON.

Schema:

{{
  "roman_minglish_transcript":"",
  "patient_name":"",
  "patient_id":"",
  "bed_number":"",
  "doctor_name":"",

  "symptoms":[
      {{
          "text":"",
          "evidence":""
      }}
  ],

  "history":[
      {{
          "text":"",
          "evidence":""
      }}
  ],

  "medications":[
      {{
          "text":"",
          "evidence":""
      }}
  ],

  "investigations":[
      {{
          "text":"",
          "evidence":""
      }}
  ],

  "pending_tasks":[
      {{
          "text":"",
          "evidence":""
      }}
  ]
}}

Transcript:

{transcript}
"""

    extraction_response = bedrock_client.converse(
        modelId="amazon.nova-lite-v1:0",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "text": extraction_prompt
                    }
                ]
            }
        ],
        inferenceConfig={
            "temperature": 0,
            "maxTokens": 4096
        }
    )

    extraction = extraction_response["output"]["message"]["content"][0]["text"]

    if extraction.startswith("```json"):
        extraction = extraction[7:-3]
    elif extraction.startswith("```"):
        extraction = extraction[3:-3]

    extraction_json = json.loads(
        extraction[
            extraction.find("{"):
            extraction.rfind("}")+1
        ]
    )

    logger.info("Clinical extraction completed.")

    generation_prompt = f"""
ROLE

You are an SBAR formatter.

You are NOT allowed to use the transcript.

Use ONLY the extracted facts below.

Never invent information.

Never infer.

If a section cannot be generated from the extracted facts,
return "Unknown".

Preserve clinical wording whenever possible.

Return ONLY JSON.

Schema

{{
"roman_minglish_transcript":"",
"situation":"",
"background":"",
"assessment":"",
"recommendation":"",
"patient_name":"",
"patient_id":"",
"bed_number":"",
"doctor_name":""
}}

Extracted Facts:

{json.dumps(extraction_json, indent=2)}
"""

    generation_response = bedrock_client.converse(
        modelId="amazon.nova-lite-v1:0",
        messages=[
            {
                "role":"user",
                "content":[
                    {
                        "text":generation_prompt
                    }
                ]
            }
        ],
        inferenceConfig={
            "temperature":0,
            "maxTokens":4096
        }
    )

    output = generation_response["output"]["message"]["content"][0]["text"]

    if output.startswith("```json"):
        output = output[7:-3]
    elif output.startswith("```"):
        output = output[3:-3]

    output_json = json.loads(
        output[
            output.find("{"):
            output.rfind("}")+1
        ]
    )

    return output_json

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
            
        # 4. Generate SBAR JSON using Bedrock
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
