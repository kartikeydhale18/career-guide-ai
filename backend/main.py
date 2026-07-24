import os
import uuid
import logging
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import boto3
from botocore.exceptions import ClientError
from openai import OpenAI
from dotenv import load_dotenv
from passlib.context import CryptContext
from boto3.dynamodb.conditions import Key

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="Career Guide AI API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust in production if needed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
LLM_API_KEY = os.getenv("LLM_API_KEY")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

if not LLM_API_KEY:
    logger.warning("LLM_API_KEY environment variable not set. Groq API calls will fail.")
    client = None
else:
    # Groq uses the exact same OpenAI SDK!
    client = OpenAI(
        api_key=LLM_API_KEY,
        base_url="https://api.groq.com/openai/v1",
    )

# Initialize DynamoDB Client
# On an EC2 instance with an IAM role attached, boto3 automatically picks up credentials.
try:
    dynamodb = boto3.resource('dynamodb', region_name=AWS_REGION)
    table = dynamodb.Table('ChatHistory')
    users_table = dynamodb.Table('Users')
except Exception as e:
    logger.error(f"Failed to initialize DynamoDB: {e}")
    table = None
    users_table = None

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Request Model
class ChatRequest(BaseModel):
    message: str
    feature_type: str = "career_advice" # career_advice, resume_tip, interview_question
    username: str

# Response Model
class ChatResponse(BaseModel):
    response: str
    status: str

# Login Request Model
class LoginRequest(BaseModel):
    username: str
    password: str

@app.post("/api/register")
async def register_endpoint(req: LoginRequest):
    if not users_table:
        raise HTTPException(status_code=500, detail="Database not configured")
        
    try:
        response = users_table.get_item(Key={'username': req.username})
        if 'Item' in response:
            raise HTTPException(status_code=400, detail="Username already exists")
            
        hashed_password = pwd_context.hash(req.password)
        users_table.put_item(
            Item={
                'username': req.username,
                'password_hash': hashed_password,
                'created_at': datetime.utcnow().isoformat()
            }
        )
        return {"success": True}
    except ClientError as e:
        logger.error(f"DynamoDB Error: {e}")
        raise HTTPException(status_code=500, detail="Database error")

@app.post("/api/login")
async def login_endpoint(req: LoginRequest):
    if not users_table:
        expected_username = os.getenv("APP_USERNAME") or "admin"
        expected_password = os.getenv("APP_PASSWORD") or "password"
        if req.username == expected_username and req.password == expected_password:
            return {"success": True}
        raise HTTPException(status_code=401, detail="Database unavailable and env invalid")
        
    try:
        response = users_table.get_item(Key={'username': req.username})
        if 'Item' not in response:
            raise HTTPException(status_code=401, detail="Invalid username or password")
            
        user = response['Item']
        if pwd_context.verify(req.password, user['password_hash']):
            return {"success": True}
        else:
            raise HTTPException(status_code=401, detail="Invalid username or password")
    except ClientError as e:
        logger.error(f"DynamoDB Error: {e}")
        raise HTTPException(status_code=500, detail="Database error")

def get_system_prompt(feature_type: str) -> str:
    base_prompt = "You are a professional and encouraging AI Career Assistant. Your goal is to help students, fresh graduates, and job seekers. "
    if feature_type == "resume_tip":
        return base_prompt + "The user is asking for help with their resume. Provide actionable, concise bullet points or structural advice to improve their resume."
    elif feature_type == "interview_question":
        return base_prompt + "The user is asking for interview preparation. Provide realistic interview questions and brief advice on how to answer them."
    else:
        return base_prompt + "Provide general career guidance, industry insights, and career path advice."

@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(req: ChatRequest):
    if not req.message or len(req.message.strip()) == 0:
        raise HTTPException(status_code=400, detail="Message cannot be empty.")
    
    if len(req.message) > 1000:
         raise HTTPException(status_code=400, detail="Message is too long. Please limit to 1000 characters.")

    if not client:
        raise HTTPException(status_code=500, detail="LLM API key not configured on server.")

    try:
        # 1. Call Groq LLM
        system_prompt = get_system_prompt(req.feature_type)
        
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant", # Groq's fast Llama 3.1 model
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": req.message},
            ],
            temperature=0.7
        )
        ai_text = response.choices[0].message.content

    except Exception as e:
        logger.error(f"LLM API Error: {e}")
        raise HTTPException(status_code=502, detail="Failed to get response from AI. Please try again later.")

    # 2. Persist to DynamoDB
    timestamp = datetime.utcnow().isoformat() + "Z"
    if table:
        try:
            table.put_item(
                Item={
                    'username': req.username,
                    'timestamp': timestamp,
                    'user_message': req.message,
                    'ai_response': ai_text,
                    'feature_type': req.feature_type
                }
            )
        except ClientError as e:
            logger.error(f"DynamoDB PutItem Error: {e.response['Error']['Message']}")
        except Exception as e:
            logger.error(f"Failed to persist to DynamoDB: {e}")
            # We don't fail the request if logging fails, but we log the error locally
    else:
         logger.warning("DynamoDB table not configured. Skipping persistence.")

    return ChatResponse(response=ai_text, status="success")

@app.get("/api/history/{username}")
async def get_history(username: str):
    if not table:
        raise HTTPException(status_code=500, detail="Database not configured")
        
    try:
        response = table.query(
            KeyConditionExpression=Key('username').eq(username),
            ScanIndexForward=True
        )
        return {"success": True, "history": response.get('Items', [])}
    except ClientError as e:
        logger.error(f"DynamoDB Query Error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch history")

# Mount frontend static files last so API routes take precedence
frontend_path = os.path.join(os.path.dirname(__file__), '..', 'frontend', 'dist')
if os.path.exists(frontend_path):
    app.mount("/", StaticFiles(directory=frontend_path, html=True), name="frontend")
else:
    logger.warning(f"Frontend dist directory not found at {frontend_path}. Static files will not be served.")
