from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
import os
import threading
import uvicorn
from azure.identity import DefaultAzureCredential
from azure.mgmt.containerinstance import ContainerInstanceManagementClient
from azure.mgmt.resource import ResourceManagementClient

from api.models import Iuser
from azure.container import create_Container, delete_Azure_container,pause_Azure_container

load_dotenv()

subId = os.getenv("SUBCRIPTIONID", "")
location = "centralindia"
PORT = os.getenv("PORT", "8080")
rg_name = "RG_vscode"
cg_name = ""
delete_timer = None

app = FastAPI()
cred = DefaultAzureCredential()
azure_container = ContainerInstanceManagementClient(credential=cred, subscription_id=subId)
rgclient = ResourceManagementClient(credential=cred, subscription_id=subId)
rgclient.resource_groups.create_or_update(resource_group_name=rg_name, parameters={
    "location": location
})

@app.post("/api/login/")
def login(user: Iuser):
    
    username,password = user.username, user.password
    print(f"Username: {username}, Password: {password}")
    if not (user.username or user.password):
        raise HTTPException(detail="Invalid Crednetial", status_code=400)
    # github_url: str = req.github_url
    global cg_name
    url, cg_name = create_Container(azure_container, username, password)
    user.vscode_url = url
    return JSONResponse(content={"message": f"Welcome {username} to the Azure Vscode", "body":user.model_dump()}, status_code=200)
    # return {"message":f"Welcome {username} to the Azure Vscode",user:user}

@app.get("/api")
def home():
    github_url: str = "https://github.com/microsoft/vscode-remote-try-python"
    command = f"""
    bash -c '
        if [ ! -d /home/coder/project ]; then 
            git clone {github_url} /home/coder/project; 
        fi && 
        code-server /home/coder/project --auth=none --port {PORT}
    '
    """
    global cg_name
    url, cg_name = create_Container(azure_container, "demouser", "code@1234", command)
    data = {"message": "Hello this is vscode server", "url": url}
    azure_container.container_groups.begin_start(rg_name, cg_name)  
    # threading.Timer(5*60, delete_Azure_container, args=(azure_container, cg_name)).start()
    threading.Timer(1*60,pause_Azure_container, args=(azure_container,)).start()  
    return JSONResponse(content=data, status_code=200)

@app.get("/api/start")
def start_container():
    global delete_timer
    print("Starting Azure Container...")
    if delete_timer is not None:
        delete_timer.cancel()
        print("Delete timer cancelled.")
        delete_timer = None
    azure_container.container_groups.begin_start(rg_name, cg_name)
    print("Azure Container Started")
    return JSONResponse(content={"message": "Container started successfully"}, status_code=200)

@app.get("/api/pause")
def pause_container():
    global delete_timer
    pause_Azure_container(azure_container)
    if delete_timer is not None:
        delete_timer.cancel()
    delete_timer = threading.Timer(5*60, delete_Azure_container, args=(azure_container, cg_name))
    delete_timer.start()
    print("Delete timer started for 5 minutes.")
    return JSONResponse(content={"message": "Container paused successfully"}, status_code=200)
    
@app.get("/api/delete")
def destroy():
    # This endpoint should receive cg_name as a query param or from session
    delete_Azure_container(azure_container)  # Replace with actual cg_name
    # For now, just a placeholder
    return JSONResponse(content={"message": "Container deleted successfully"}, status_code=200)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=3000)
