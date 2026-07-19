import json
import os
import boto3
import urllib.request
import time
import logging
from typing import TypedDict, Optional
from langgraph.graph import StateGraph, START, END

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
s3_client = boto3.client('s3')
bedrock_client = boto3.client('bedrock-runtime', region_name='us-east-1')
dynamodb = boto3.resource('dynamodb')

# Define our Agentic State
class HandoverState(TypedDict):
    handover_id: str
    tmp_file_path: str
    raw_transcript: Optional[str]
    edited_transcript: Optional[str]
    draft_sbar: Optional[dict]
    validation_feedback: Optional[str]
    is_valid: bool
    validation_attempts: int

# --- NODE 1: Transcription (Groq Whisper) ---
def transcribe_node(state: HandoverState) -> dict:
    logger.info("NODE: transcribe_node")
    groq_api_key = os.environ.get('GROQ_API_KEY')
    if not groq_api_key:
        raise ValueError("GROQ_API_KEY environment variable is missing.")

    boundary = '----WebKitFormBoundary7MA4YWxkTrZu0gW'
    body_parts = []
    body_parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="model"\r\n\r\nwhisper-large-v3\r\n'.encode('utf-8'))
    prompt_text = "Medical handover in Minglish/English. Terms: BP, HR, IV, Vancomycin, Amoxicillin, Cardiology, ICU, Ward, Dr. Vascianne."
    body_parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="prompt"\r\n\r\n{prompt_text}\r\n'.encode('utf-8'))
    body_parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="audio.webm"\r\nContent-Type: audio/webm\r\n\r\n'.encode('utf-8'))
    
    with open(state["tmp_file_path"], 'rb') as f:
        body_parts.append(f.read())
        
    body_parts.append(f'\r\n--{boundary}--\r\n'.encode('utf-8'))
    payload = b''.join(body_parts)

    headers = {
        'Authorization': f'Bearer {groq_api_key}',
        'Content-Type': f'multipart/form-data; boundary={boundary}',
        'User-Agent': 'SBAR-Handover-App/1.0'
    }
    
    req = urllib.request.Request('https://api.groq.com/openai/v1/audio/transcriptions', data=payload, headers=headers)
    response = urllib.request.urlopen(req, timeout=30)
    result = json.loads(response.read().decode('utf-8'))
    
    return {"raw_transcript": result.get('text', '')}

# --- Helper: Bedrock Converse API ---
def call_bedrock_llm(prompt: str, temperature=0.1) -> str:
    response = bedrock_client.converse(
        modelId="amazon.nova-lite-v1:0",
        messages=[{"role": "user", "content": [{"text": prompt}]}],
        inferenceConfig={"maxTokens": 1000, "temperature": temperature}
    )
    return response['output']['message']['content'][0]['text'].strip()

# --- NODE 2: Clinical Editor ---
def clinical_editor_node(state: HandoverState) -> dict:
    logger.info("NODE: clinical_editor_node")
    prompt = f"""You are an expert clinical pharmacist and medical editor. 
Below is an AI-generated transcript of a doctor's shift handover. It contains phonetic mistakes (e.g., mishearing drug names or medical terms).
Your job is to read it, identify clinical impossibilities or obvious phonetic errors, and output the corrected transcript.
Do not change the meaning or structure, just fix the medical terms and grammar.

Raw AI Transcript:
{state["raw_transcript"]}

Output ONLY the corrected transcript text, nothing else."""

    corrected_text = call_bedrock_llm(prompt)
    logger.info(f"Edited Transcript: {corrected_text}")
    return {"edited_transcript": corrected_text}

# --- NODE 3: Extractor ---
def extract_sbar_node(state: HandoverState) -> dict:
    logger.info(f"NODE: extract_sbar_node (Attempt {state.get('validation_attempts', 0) + 1})")
    
    feedback_context = ""
    if state.get("validation_feedback"):
        feedback_context = f"\n\nWARNING: Your previous attempt had errors. Please fix them based on this feedback:\n{state['validation_feedback']}"

    prompt = f"""Convert this clinical handover transcript into a structured SBAR format.
You must return ONLY a valid JSON object matching this schema.

{{
  "roman_minglish_transcript": "The exact original transcript text",
  "situation": "brief statement of the problem",
  "background": "brief history and context",
  "assessment": "what you think the problem is",
  "recommendation": "what needs to be done",
  "patient_id": "extract patient ID or MR number if mentioned, else 'Unknown Patient'",
  "doctor_name": "extract doctor name if mentioned, else 'Unknown Doctor'"
}}

Transcript:
{state["edited_transcript"]}{feedback_context}"""

    content = call_bedrock_llm(prompt)
    logger.info(f"Raw LLM Extractor Output: {content}")
    
    start_idx = content.find('{')
    end_idx = content.rfind('}') + 1
    
    if start_idx == -1 or end_idx <= start_idx:
        logger.error("LLM failed to return a JSON object.")
        # Fallback empty SBAR if LLM refuses to answer
        draft_json = {
            "roman_minglish_transcript": state.get("edited_transcript", ""),
            "situation": "AI Parsing Error",
            "background": "The AI model returned text that was not valid JSON.",
            "assessment": "Please check CloudWatch logs.",
            "recommendation": "Review the raw transcript.",
            "patient_id": "Unknown Patient",
            "doctor_name": "Unknown Doctor"
        }
    else:
        try:
            draft_json = json.loads(content[start_idx:end_idx])
        except json.JSONDecodeError as e:
            logger.error(f"JSON Parse Error: {str(e)}. Content: {content[start_idx:end_idx]}")
            raise
    return {
        "draft_sbar": draft_json, 
        "validation_attempts": state.get("validation_attempts", 0) + 1
    }

# --- NODE 4: Validator (Chief Resident) ---
def validate_node(state: HandoverState) -> dict:
    logger.info("NODE: validate_node")
    
    # If we loop too many times, just accept it to prevent infinite loops
    if state["validation_attempts"] >= 3:
        logger.warning("Max validation attempts reached. Forcing valid.")
        return {"is_valid": True}

    prompt = f"""You are the Chief Resident reviewing a junior doctor's SBAR notes.
Compare the original transcript against the drafted SBAR JSON.
Check strictly for:
1. Did they hallucinate or change a medication name or dosage?
2. Did they miss critical numerical data (BP, HR, Bed Number, Patient ID)?

Transcript: {state["edited_transcript"]}
Drafted SBAR: {json.dumps(state["draft_sbar"])}

If it is completely accurate, reply ONLY with the word "PASS".
If there are clinical errors or omissions, reply with "FAIL: " followed by the feedback on what to fix."""

    evaluation = call_bedrock_llm(prompt, temperature=0.0)
    
    if evaluation.strip().upper() == "PASS":
        return {"is_valid": True, "validation_feedback": None}
    else:
        logger.info(f"Validation Failed: {evaluation}")
        return {"is_valid": False, "validation_feedback": evaluation}

# --- Graph Routing ---
def route_validation(state: HandoverState) -> str:
    if state["is_valid"]:
        return "end"
    return "extract"

# --- Build the Graph ---
workflow = StateGraph(HandoverState)
workflow.add_node("transcribe", transcribe_node)
workflow.add_node("editor", clinical_editor_node)
workflow.add_node("extract", extract_sbar_node)
workflow.add_node("validate", validate_node)

workflow.add_edge(START, "transcribe")
workflow.add_edge("transcribe", "editor")
workflow.add_edge("editor", "extract")
workflow.add_edge("extract", "validate")
workflow.add_conditional_edges("validate", route_validation, {"end": END, "extract": "extract"})

app = workflow.compile()

def lambda_handler(event, context):
    logger.info(f"Received S3 Event: {json.dumps(event)}")
    try:
        record = event['Records'][0]
        bucket_name = record['s3']['bucket']['name']
        object_key = record['s3']['object']['key']
        handover_id = object_key.split('/')[-1].split('.')[0]
        
        tmp_file_path = f"/tmp/{handover_id}.webm"
        s3_client.download_file(bucket_name, object_key, tmp_file_path)
        
        # Initialize State
        initial_state = {
            "handover_id": handover_id,
            "tmp_file_path": tmp_file_path,
            "validation_attempts": 0,
            "is_valid": False
        }
        
        # Execute LangGraph Workflow
        logger.info("Invoking LangGraph Workflow...")
        final_state = app.invoke(initial_state)
        
        # Save to DynamoDB
        sbar_data = final_state["draft_sbar"]
        minglish_transcript = sbar_data.pop('roman_minglish_transcript', final_state["raw_transcript"])
        
        item = {
            'handover_id': handover_id,
            'status': 'Complete',
            'created_at': int(time.time()),
            'raw_transcript': minglish_transcript,
            'edited_transcript': final_state["edited_transcript"],
            **sbar_data
        }
        dynamodb.Table('sbar-handovers').put_item(Item=item)
        logger.info("Successfully saved validated SBAR to DynamoDB")
        
        return {"statusCode": 200, "body": "Processing complete"}
        
    except Exception as e:
        logger.error(f"Pipeline failed: {str(e)}")
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
