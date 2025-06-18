from fastapi import FastAPI, HTTPException
from fastapi.requests import Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uuid
import uvicorn
from azure.mgmt.containerinstance import ContainerInstanceManagementClient
from azure.mgmt.resource import ResourceManagementClient
from azure.identity import DefaultAzureCredential
import threading

subId = 
location = "centralindia"
PORT = 8080
rg_name = "RG_vscode"
image="ghcr.io/coder/code-server:latest"
username="demouser"
password="code@1234"

class Iuser(BaseModel,Request):
    username:str
    password:str

app = FastAPI()
cred = DefaultAzureCredential()
azure_container = ContainerInstanceManagementClient(credential=cred, subscription_id=subId)
rgclient = ResourceManagementClient(credential=cred, subscription_id=subId)
rgclient.resource_groups.create_or_update(resource_group_name=rg_name,parameters={
    "location":location
})

sessionid = uuid.uuid4().hex[:6]
cg_name = f"{username}-code-{sessionid}"

def create_Container(username:str=username,password:str=password):

    azure_container.container_groups.begin_create_or_update(
        rg_name,
        cg_name,
        {
            "location":location,
            "os_type":"Linux",
            "containers":[{
                "name":"vscode-server",
                "image":image,
                "resources":{
                    "requests":{
                        "cpu":1,
                        "memory_in_gb":1.5,
                    }
                },
                "ports":[
                    {
                        "port":PORT
                    }
                ],
                "environment_variables": [  # ✅ Add environment variable
                    {
                        "name": "PASSWORD",
                        "value": password
                    }
                ]
        }],
             "ip_address":{
                    "ports":[{
                        "protocol":"TCP",
                        "port":PORT 
                    }],
                    "type":"Public",
                    "dns_name_label": cg_name
                }
        }
    ).result()
    print("Azure Container Created")
    return  f"http://{cg_name}.{location}.azurecontainer.io:{PORT}"


def delete_Azure_container(cg_name:str):
    azure_container.container_groups.begin_delete(resource_group_name=rg_name,container_group_name=cg_name)
    azure_container
    print("Azure Container Deleted")

@app.post("/api/login")
def login(req: Iuser):
    if (req.username != "") or (req.password != ""):
        raise HTTPException(detail="Invalid Crednetial", status_code=400)
    url = create_Container(req.username,req.password)
    return {"url":url}


@app.get("/api")
def home():
    url = create_Container()
    data =  {"message":"Hello this is vscode server", "url":url}
    return JSONResponse(content=data, status_code=200)

@app.get("/api/delete")
def destroy():
    # threading.Timer(5*60,delete_Azure_container(cg_name)).start()
    delete_Azure_container(cg_name)


if __name__ == "__main__":
    uvicorn.run(app,host="0.0.0.0",port=3000)