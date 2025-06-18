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
from azure.mgmt.containerinstance import ContainerInstanceManagementClient
from fastapi import HTTPException
import uuid
import os

PORT = os.getenv("PORT", "8080")
location = "centralindia"
image = "ghcr.io/coder/code-server:latest"
rg_name = "RG_vscode"
cg_name = ""


def create_Container(azure_container, username, password, command:str=""):
    sessionid = uuid.uuid4().hex[:6]
    global cg_name
    cg_name = f"{username}-code-{sessionid}"
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
        # command=["bash", "-c", command],
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
    return f"http://{cg_name}.{location}.azurecontainer.io:{PORT}", cg_name

def delete_Azure_container(azure_container):
    print("Deleting Azure Container...")
    if not cg_name:
        raise HTTPException(detail="Container group name is required", status_code=400)
    azure_container.container_groups.begin_delete(resource_group_name=rg_name, container_group_name=cg_name)
    print("Azure Container Deleted")

def pause_Azure_container(azure_container:ContainerInstanceManagementClient):
    print("Pausing Azure Container...")
    if not cg_name:
        raise HTTPException(detail="Container group name is required", status_code=400)
    azure_container.container_groups.stop(resource_group_name=rg_name, container_group_name=cg_name)
    print("Azure Container Paused")
