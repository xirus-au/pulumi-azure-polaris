import json
import os

import pulumi
from pulumi import Output, ResourceOptions
from pulumi_azure.containerservice import KubernetesCluster, Registry
from pulumi_azure.core import ResourceGroup
from pulumi_azure.cosmosdb import Account, SqlContainer, SqlDatabase, Table
from pulumi_azure.network import Subnet, VirtualNetwork
from pulumi_azure.role import Assignment
from pulumi_azuread import (Application, ServicePrincipal,
                            ServicePrincipalPassword)
from pulumi_kubernetes import Provider
from pulumi_kubernetes.apps.v1 import Deployment
from pulumi_kubernetes.core.v1 import Service

import docker

# read and set config values
config = pulumi.Config("pulumi-api-aks")

PREFIX = config.require("prefix")
PASSWORD = config.require_secret("password")
SSHKEY = config.require("sshkey")
LOCATION = config.get("location") or "east us"
VNETADDRESSSPACE = config.get("vnetAddressSpace")
SUBNETADDRESSSPACE = config.get("subnetAddressSpace")
AKSSERVICECIDR = config.get("aksServiceCidr")
DNSSERVICEIP = config.get("dnsServiceIP")
VMSIZE = config.get("vmSize")
DOCKER_TAG = config.get("dockerTag")
DOCKER_REPO_URI = PREFIX + "acr" + ".azurecr.io" + DOCKER_TAG

# docker client
dockerclient = docker.from_env()

if pulumi.runtime.is_dry_run() == False:
    image, log = dockerclient.images.build(
        path="./",
        tag=PREFIX + "acr" + DOCKER_TAG
    )
    for line in log:
        print(line)

# create resource group
resource_group = ResourceGroup("rg", name=pulumi.get_stack() + "rg", location=LOCATION)

vnet = VirtualNetwork(
    "vnet",
    name=PREFIX + "vnet",
    resource_group_name=resource_group.name,
    address_spaces=[VNETADDRESSSPACE],
    __opts__=ResourceOptions(parent=resource_group),
)

subnet = Subnet(
    "subnet",
    name=PREFIX + "subnet",
    resource_group_name=resource_group.name,
    address_prefix=SUBNETADDRESSSPACE,
    virtual_network_name=vnet.name,
    __opts__=ResourceOptions(parent=vnet),
)

# create Azure Container Registry to store images in
acr = Registry(
    "acr",
    name=PREFIX + "acr",
    admin_enabled=True,
    resource_group_name=resource_group.name,
    sku="basic",
    __opts__=ResourceOptions(parent=resource_group),
)

def docker_login_and_push(args):
    dockerclient.login(
            registry=args[0],
            username=args[1],
            password=args[2]
        )
    for line in dockerclient.images.push(repository=DOCKER_REPO_URI, stream=True, decode=True):
        print(line)

# Push docker image to ACR
Output.all(acr.login_server, acr.admin_username,
        acr.admin_password).apply(docker_login_and_push)

# create Azure AD Application for AKS
app = Application("aks-app", name=PREFIX + "aks-app")

# create service principal for the application so AKS can act on behalf of the application
sp = ServicePrincipal(
    "aks-app-sp",
    application_id=app.application_id,
    __opts__=ResourceOptions(parent=app),
)

# create service principal password
sppwd = ServicePrincipalPassword(
    "aks-app-sp-pwd",
    service_principal_id=sp.id,
    end_date="2025-01-01T01:02:03Z",
    value=PASSWORD,
    __opts__=ResourceOptions(parent=sp),
)

# assignments are needed for AKS to be able to interact with those resources
acr_assignment = Assignment(
    "aks-acr-permissions",
    principal_id=sp.id,
    role_definition_name="AcrPull",
    scope=acr.id,
    __opts__=ResourceOptions(parent=sp),
)

subnet_assignment = Assignment(
    "aks-subnet-permissions",
    principal_id=sp.id,
    role_definition_name="Network Contributor",
    scope=subnet.id,
    __opts__=ResourceOptions(parent=sp),
)

aks = KubernetesCluster(
    "aks",
    name=PREFIX + "aks",
    resource_group_name=resource_group.name,
    kubernetes_version="1.15.5",
    dns_prefix="dns",
    agent_pool_profiles=[
        {
            "name": "type1",
            "count": 2,
            "enableAutoScaling": True,
            "maxPods": 110,
            "min_count": 2,
            "max_count": 4,
            "osType": "Linux",
            "type": "VirtualMachineScaleSets",
            "vmSize": VMSIZE,
            "vnet_subnet_id": subnet.id,
        }
    ],
    linux_profile={"adminUsername": "azureuser", "ssh_key": {"keyData": SSHKEY}},
    service_principal={"clientId": app.application_id, "clientSecret": sppwd.value},
    role_based_access_control={"enabled": "false"},
    network_profile={
        "networkPlugin": "azure",
        "serviceCidr": AKSSERVICECIDR,
        "dns_service_ip": DNSSERVICEIP,
        "dockerBridgeCidr": "172.17.0.1/16",
    },
    __opts__=ResourceOptions(
        parent=resource_group, depends_on=[acr_assignment, subnet_assignment]
    ),
)

k8s_provider = Provider(
    "k8s", kubeconfig=aks.kube_config_raw, __opts__=ResourceOptions(parent=aks)
)

cosmos_db_account = Account(
    "cosmosdbaccount",
    consistency_policy={
        "consistencyLevel": "Strong"
    },
    geo_locations=[
        {
        "location": resource_group.location,
        "failoverPriority":0
        }
    ],
    kind="GlobalDocumentDB",
    offer_type="Standard",
    resource_group_name=resource_group.name
)

cosmos_db_database = SqlDatabase(
    "cosmosdbdatabase",
    account_name=cosmos_db_account.name,
    name="tickets",
    resource_group_name=resource_group.name
)

cosmos_db_container = SqlContainer(
    "cosmosdbcontainer",
    account_name=cosmos_db_account.name,
    database_name=cosmos_db_database.name,
    name="tickets",
    resource_group_name=resource_group.name
)

labels = {"app": "polaris"}
polaris = Deployment(
    "k8s-polaris-deployment1",
    spec={
        "selector": {"matchLabels": labels},
        "replicas": 15,
        "template": {
            "metadata": {"labels": labels},
            "spec": {"containers": [{"name": "polaris", "image": DOCKER_REPO_URI, "env":[{"name": "cosmosKey", "value": cosmos_db_account.primary_master_key}, {"name": "cosmosDbAccountName", "value": cosmos_db_account.name}, {"name": "cosmodDbDatabaseName", "value": cosmos_db_database.name}, {"name": "cosmosDbCollectionId", "value": cosmos_db_container.name}] }]},
        },
    },
    __opts__=ResourceOptions(parent=k8s_provider, provider=k8s_provider),
)

ingress = Service(
    "k8s-polaris-service",
    spec={"type": "LoadBalancer", "selector": labels, "ports": [{"port": 8080}]},
    __opts__=ResourceOptions(parent=k8s_provider, provider=k8s_provider),
)
pulumi.export("ingress_ip", ingress)
pulumi.export("kubeconfig", aks.kube_config_raw)
pulumi.export("cosmos_db_account_name", cosmos_db_account.name)
pulumi.export("cosmos_db_container_name", cosmos_db_container.name)
pulumi.export("acr_login_server", acr.login_server)
pulumi.export("acr_password", acr.admin_password)
pulumi.export("acr_username", acr.admin_username)
