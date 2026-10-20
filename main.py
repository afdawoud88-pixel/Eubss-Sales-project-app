import os
import jwt
from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client, Client
from pydantic import BaseModel
from typing import List
from dotenv import load_dotenv
from twilio.rest import Client as TwilioClient

load_dotenv()

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

class ProjectCreate(BaseModel):
    client_id: str
    name: str
    total_value: float
    milestones: List[MilestoneCreate]
    tasks: List[TaskCreate]

class TaskUpdate(BaseModel):
    status: str

... class AttachmentUpdate(BaseModel):
...     url: str
... 
... # 4. مسارات (Endpoints) النظام
... @app.get("/api/vendor-payments/all")
... def get_all_vendor_payments(user: dict = Depends(verify_token)):
...     return {"data": supabase.table("purchase_orders").select("*, vendors(name), projects(name)").execute().data}
... 
... @app.get("/api/client-milestones/pending")
... def get_pending_milestones(user: dict = Depends(verify_token)):
...     return {"data": supabase.table("client_milestones").select("*, projects(name)").eq("status", "Pending").execute().data}
... 
... @app.put("/api/client-milestones/{milestone_id}")
... def update_client_milestone(milestone_id: str, payload: MilestoneUpdate, user: dict = Depends(verify_token)):
...     supabase.table("client_milestones").update({"status": payload.status}).eq("id", milestone_id).execute()
...     return {"message": "تم التحصيل"}
... 
... @app.put("/api/traffic-tasks/{task_id}")
... def update_traffic_status(task_id: str, payload: TaskUpdate, user: dict = Depends(verify_token)):
...     supabase.table("purchase_orders").update({"traffic_status": payload.status}).eq("id", task_id).execute()
...     return {"message": "تم تحديث الحالة"}
... 
... @app.put("/api/traffic-tasks/{task_id}/attachment")
... def update_task_attachment(task_id: str, payload: AttachmentUpdate, user: dict = Depends(verify_token)):
...     supabase.table("purchase_orders").update({"attachment_url": payload.url}).eq("id", task_id).execute()
...     return {"message": "تم حفظ الرابط"}
... 
... @app.post("/api/projects/new")
... def create_new_project(payload: ProjectCreate, user: dict = Depends(verify_token)):
...     proj = supabase.table("projects").insert({"client_id": payload.client_id, "name": payload.name, "total_value": payload.total_value}).execute()
...     proj_id = proj.data[0]['id']
...     
...     ms_ids = []
...     for ms in payload.milestones:
...         res = supabase.table("client_milestones").insert({"project_id": proj_id, "title": ms.title, "amount": ms.amount}).execute()
...         ms_ids.append(res.data[0]['id'])
... 
...     for task in payload.tasks:
...         supabase.table("purchase_orders").insert({
...             "project_id": proj_id, "vendor_id": task.vendor_id,
...             "linked_client_milestone_id": ms_ids[task.linked_milestone_index],
...             "description": task.description, "amount": task.amount
...         }).execute()
... 
...     send_whatsapp_to_ops(payload.name, len(payload.tasks))
