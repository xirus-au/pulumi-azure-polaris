$VerbosePreference = 'Continue'
$cosmosKey = ConvertTo-SecureString -String $env:cosmosKey -AsPlainText -Force 
$cosmosDbContext = New-CosmosDbContext -Account $env:cosmosDbAccountName -Database $env:cosmodDbDatabaseName -Key $cosmosKey

New-PolarisPostRoute -Path '/users' -Scriptblock {
    $firstName = $Request.Query['firstname']
    $lastName = $Request.Query['lastname']
    $location = $Request.Query['location']
    $document = @"
    {
        `"id`": `"$([Guid]::NewGuid().ToString())`",
        `"firstname`": `"$firstName`",
        `"lastname`": `"$lastName`",
        `"location`": `"$location`"
    }
"@
    $retDocument = New-CosmosDbDocument -Context $cosmosDbContext -CollectionId $env:cosmosDbCollectionId -DocumentBody $document
    Write-Host $retDocument
    $Response.Send("Thanks $firstName, for adding your information. Your ticket ID is $($retDocument.id).")
}

New-PolarisGetRoute -Path '/users' -Scriptblock {
    Write-Host "$($Request.Query)"
    if ($($Request.Query).count -eq 0) {
        $query = "SELECT * FROM c"
        Write-Host 'get them all'
        $result = Get-CosmosDbDocument -Context $cosmosDbContext -CollectionId $env:cosmosDbCollectionId -Query $query
    }
    else {
        Write-Host 'get only one'
        $ticketId = $Request.Query['ticketid']
        $query = "SELECT * FROM c WHERE (c.id = `"$ticketId`")"
        $result = Get-CosmosDbDocument -Context $cosmosDbContext -CollectionId $env:cosmosDbCollectionId -Query $query
    }
    if ($result) {
        $Response.Send(($result | ConvertTo-Json))
    }
}

Start-Polaris -Port 8080 -MinRunspaces 3 -MaxRunspaces 10

while ($true) {
    Start-sleep -seconds 10
}