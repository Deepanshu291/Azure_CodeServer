from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.requests import Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uuid
import uvicorn
from azure.mgmt.containerinstance import ContainerInstanceManagementClient
from azure.mgmt.resource import ResourceManagementClient
from azure.identity import DefaultAzureCredential
import threading
from azure.mgmt.containerinstance.models import (
    ContainerGroup,
    Container,
    ResourceRequests,
    ResourceRequirements,
    Port,
    ContainerPort,
    EnvironmentVariable,
    IpAddress,
    ContainerGroupNetworkProtocol,
    OperatingSystemTypes
)
from dotenv import load_dotenv
import os


load_dotenv()

subId = os.getenv("SUBCRIPTIONID","")
location = "centralindia"
PORT = os.getenv("PORT","8080")  
rg_name = "RG_vscode"
image="ghcr.io/coder/code-server:latest"
username="demouser"
password="code@1234"

class Iuser(BaseModel,Request):
    username:str
    password:str
    github_url:str = "https://github.com/microsoft/vscode-remote-try-python"

app = FastAPI()
cred = DefaultAzureCredential()
azure_container = ContainerInstanceManagementClient(credential=cred, subscription_id=subId)
rgclient = ResourceManagementClient(credential=cred, subscription_id=subId)
rgclient.resource_groups.create_or_update(resource_group_name=rg_name,parameters={
    "location":location
})

sessionid = uuid.uuid4().hex[:6]
cg_name = f"{username}-code-{sessionid}"



def create_Container(username:str=username, password:str=password, command:str=f"code-server --auth=none --port {PORT}"):
    print("Creating Azure Container...")
    
    if not username or not password:
        raise HTTPException(detail="Username and password are required", status_code=400)
    container_resource_requests = ResourceRequests(cpu=1, memory_in_gb=1.5)
    container_resource_requirements = ResourceRequirements(requests=container_resource_requests)
    container_ports = [ContainerPort(port=int(PORT))]
    environment_variables = [EnvironmentVariable(name="PASSWORD", value=password)]
    container = Container(
        name="vscode-server",
        image=image,
        resources=container_resource_requirements,
        ports=container_ports,
        environment_variables=environment_variables,
        command=["bash", "-c", "git", "clone", "https://github.com/microsoft/vscode-remote-try-python", "/home/coder/project", "&&", "code-server", "/home/coder/project", "--auth=none", "--port", str(PORT)],
    )
    ip_address = IpAddress(
        ports=[Port(protocol=ContainerGroupNetworkProtocol.tcp.value, port=int(PORT))],
        type="Public",
        dns_name_label=cg_name
    )
    container_group = ContainerGroup(
        location=location,
        containers=[container],
        os_type=OperatingSystemTypes.LINUX,
        ip_address=ip_address,
    )
    azure_container.container_groups.begin_create_or_update(
        rg_name,
        cg_name,
        container_group
    ).result()
    print("Azure Container Created")
    return f"http://{cg_name}.{location}.azurecontainer.io:{PORT}"


def delete_Azure_container(cg_name:str):
    print("Deleting Azure Container...")
    if not cg_name:
        raise HTTPException(detail="Container group name is required", status_code=400)
    azure_container.container_groups.begin_delete(resource_group_name=rg_name,container_group_name=cg_name)
    # azure_container
    print("Azure Container Deleted")

@app.post("/api/login")
def login(req: Iuser):
    if (req.username != "") or (req.password != ""):
        raise HTTPException(detail="Invalid Crednetial", status_code=400)
    github_url: str = "https://github.com/microsoft/vscode-remote-try-python"
    command = f"""
    bash -c '
        if [ ! -d /home/coder/project ]; then 
            git clone {github_url} /home/coder/project; 
        fi && 
        code-server /home/coder/project --auth=none --port {PORT}
    '
    """
    url = create_Container(req.username, req.password, command)
    return {"url": url}


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
    url = create_Container(command=command)
    # url = create_Container()
    data =  {"message": "Hello this is vscode server", "url": url}
    threading.Timer(5*60, delete_Azure_container, args=(cg_name,)).start()
    return JSONResponse(content=data, status_code=200)

@app.get("/api/delete")
def destroy():
    delete_Azure_container(cg_name)
    return JSONResponse(content={"message": "Container deleted successfully"}, status_code=200)


if __name__ == "__main__":
    uvicorn.run(app,host="0.0.0.0",port=3000)