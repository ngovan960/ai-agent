import requests
import json
import time

print("Creating Project...")
proj_resp = requests.post("http://localhost:8000/api/v1/projects/", json={
    "name": "Test Project 2",
    "description": "Testing OpenCode CLI"
})
proj_data = proj_resp.json()
print(f"Project Created: {proj_data.get('id')}")

project_id = proj_data.get('id')
if not project_id:
    print(f"Failed to create project: {proj_data}")
    exit(1)

print("Creating Task...")
task_resp = requests.post("http://localhost:8000/api/v1/tasks/", json={
    "title": "Tạo trang web profile đơn giản 2",
    "description": "Create a simple profile page with HTML and CSS",
    "project_id": project_id,
    "priority": "medium",
    "owner": "admin"
})
task_data = task_resp.json()
task_id = task_data.get('id')
print(f"Task Created: {task_id}")

for i in range(15):
    time.sleep(2)
    status_resp = requests.get(f"http://localhost:8000/api/v1/tasks/{task_id}")
    status = status_resp.json().get('status')
    print(f"[{i}] Task Status: {status}")

