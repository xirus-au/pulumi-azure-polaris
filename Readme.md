# Pulumi - Azure AKS and PowerShell Polaris API

This repo can be used to deploy a demo application running a PowerShell Polaris API inside a container running on Azure Kubernetes Services (AKS) which communicates with CosmosDB as its backend.

## Prerequisites

1. [Install Pulumi](https://www.pulumi.com/docs/get-started/install/)
2. [Install Python 3.6](https://www.python.org/downloads/)
3. [Configure Azure Credentials](https://www.pulumi.com/docs/intro/cloud-providers/azure/setup/)
4. [Generate SSH Key](https://git-scm.com/book/en/v2/Git-on-the-Server-Generating-Your-SSH-Public-Key)
5. [docker installed](https://docs.docker.com/install/)

## Steps

After cloning this repo, from this working directory, run these commands:

1. Install the required Python packages packages:

    ```bash
    pip install -r requirements.txt
    ```

2. Create a new stack, which is an isolated deployment target for this example:

    ```bash
    pulumi stack init
    ```

3. Set the configuration variables for this program:

    ```bash
    pulumi config set aksServiceCidr 10.10.0.0/16
    pulumi config set dnsServiceIP 10.10.0.10
    pulumi config set dockerTag /conf/london
    pulumi config set location any_valid_azure_location_for_aks
    pulumi config set --secret password service_principal_password
    pulumi config set prefix all_resources_will_be_prefixed_with_this_value
    pulumi config set sshkey < ~/.ssh/id_rsa.pub
    pulumi config set subnetAddressSpace 10.0.0.0/24
    pulumi config set vmSize Standard_B2ms
    pulumi config set vnetAddressSpace 10.0.0.0/16
    ```

4. Build the docker image, deploy the infrastructure and the app:

    ```bash
    pulumi up
    ```

5. After 10-15 minutes, your cluster will be ready, and the kubeconfig YAML you'll use to connect to the cluster will be available as an output. You can save this kubeconfig to a file like so:

    ```bash
    pulumi stack output kubeconfig > kubeconfig.yaml
    ```

    Once you have this file in hand, you can interact with your new cluster as usual via `kubectl`:

    ```bash
    KUBECONFIG=./kubeconfig.yaml kubectl get nodes
    ```

    Or browse to the kubernetes dashboard like this:

    ```bash
    KUBECONFIG=./kubeconfig.yaml az aks browse --resource-group <aksResourceGroupName> --name <aksClusterName>
    ```

6. Once the stack is deployed into your Azure subscription pulumi will show you several `Outputs`, one of which is the `ingress_ip`.
    Access the API via PowerShell (`curl`, postman, etc) like this:

    ```powershell
    Invoke-RestMethod -Method Post 'http://<ingressIp>:8080/users?firstname=David&lastname=OBrien&location=Geelong'
    Invoke-RestMethod -Method Get 'http://<ingressIp>:8080/users'
    ```

## Teardown

Be aware that these resources will cost money, so once you are done testing and when you don't need the resources anymore, delete them all by running

  ```bash
  pulumi destroy
  ```

## Improvements

* Enable https on endpoint
* Add domain name to endpoint
* Make Polaris more stable
* Split components out into modules