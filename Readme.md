# Pulumi - Azure AKS and PowerShell Polaris API

This repo can be used to deploy a demo application running a PowerShell Polaris API inside a container running on Azure Kubernetes Services (AKS) which communicates with CosmosDB as its backend.

### Prerequisites

1. [Install Pulumi](https://www.pulumi.com/docs/get-started/install/)
2. [Install Python 3.6](https://www.python.org/downloads/)
3. [Configure Azure Credentials](https://www.pulumi.com/docs/intro/cloud-providers/azure/setup/)
4. [Generate SSH Key](https://git-scm.com/book/en/v2/Git-on-the-Server-Generating-Your-SSH-Public-Key)

### Steps

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
    pulumi config set prefix all_resources_will_be_prefixed_with_this_value
    pulumi config set password service_principal_password
    pulumi config set sshkey < ~/.ssh/id_rsa.pub
    # this has a default value, so you can skip it
    pulumi config set location any_valid_azure_location_for_aks
    ```

4. Stand up the AKS cluster and CosmosDB account:

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

6. The application however will not work yet as the docker image has not been uploaded to Azure Container Registry. Once Pulumi natively supports running docker, this will be taken care of by Pulumi.

  ```bash
  # use the prefix you configure in pulumi to build the ACR name
  az acr login --name <PREFIX>acr
  # build the docker image
  docker build -t <PREFIX>acr.azurecr.io/conf/polaris .
  docker push <PREFIX>acr.azurecr.io/conf/polaris
  ```

7. If the previous Pulumi script failed (likely!) then just run `pulumi up` again.

### Teardown

Be aware that these resources will cost money, so once you are done testing and when you don't need the resources anymore, delete them all by running

  ```bash
  pulumi destroy
  ```

