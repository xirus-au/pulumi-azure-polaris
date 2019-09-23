FROM microsoft/powershell:preview-centos-7
RUN pwsh -Command Install-Module Polaris -Force
RUN pwsh -Command Install-Module CosmosDB -Force
COPY  /website /app
WORKDIR /app
EXPOSE 8080

ENTRYPOINT ["pwsh", "./Start-Website.ps1" ]