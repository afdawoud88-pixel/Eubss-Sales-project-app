import os
import jwt
from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client, Client
from pydantic import BaseModel
from typing import List
from dotenv import load_dotenv
from twilio.rest import Client as TwilioClient

# تحميل متغيرات البيئة
load_dotenv()

# إعداد الاتصال بقاعدة بيانات Supabase
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
SUPABASE_JWT_SECRET = os.environ.get("SUPABASE_JWT_SECRET")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

app = FastAPI(title="Agency ERP API")

# السماح لأي واجهة بالاتصال بالخادم (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 1. دالة التحقق من الأمان (JWT)
def verify_token(authorization: str = Header(...)):
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise HTTPException(status_code=401, detail="تنسيق غير صالح")
        payload = jwt.decode(token, SUPABASE_JWT_SECRET, algorithms=["HS256"], audience="authenticated")
        return payload
    except Exception:
        raise HTTPException(status_code=401, detail="غير مصرح لك بالوصول")

# 2. دالة إشعارات الواتساب
def send_whatsapp_to_ops(project_name: str, tasks_count: int):
    try:
        client = TwilioClient(os.environ.get("TWILIO_ACCOUNT_SID"), os.environ.get("TWILIO_AUTH_TOKEN"))
        client.messages.create(
            body=f"🚨 *مشروع جديد: {project_name}*\nتم إدراج {tasks_count} مهام للتشغيل.",
            from_=os.environ.get("TWILIO_WHATSAPP_NUMBER"),
            to=os.environ.get("OPS_MANAGER_PHONE")
        )
    except Exception as e:
        print(f"WhatsApp Error: {e}")

# 3. النماذج (Models)
class MilestoneUpdate(BaseModel):
    status: str

class MilestoneCreate(BaseModel):
    title: str
    amount: float
class TaskCreate(BaseModel):
    vendor_id: str
    description: str
    amount: float
    linked_milestone_index: int
