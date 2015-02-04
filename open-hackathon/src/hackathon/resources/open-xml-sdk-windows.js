{
    "expr_name": "windows",
    "description" : "one storage account, one container, one cloud service, one deployment, multiple virtual machines (Windows/Linux), multiple input endpoints",
    "storage_account" : {
        "service_name" : "opentech0storage",
        "description" : "storage-description",
        "label" : "storage-label",
        "location" : "China East",
        "url_base" : "blob.core.chinacloudapi.cn"
    },
    "container" : "open-tech-container",
    "cloud_service" : {
        "service_name" : "open-tech-cloud-service",
        "label" : "cloud-service-label",
        "location" : "China East"
    },
    "deployment" :{
        "deployment_name" : "open-tech-deployment",
        "deployment_slot" : "production"
    },
    "virtual_environments": [
        {
            "provider": "azure",
            "label" : "role-label",
            "role_name" : "open-tech-role",
            "system_config" : {
                "os_family" : "Windows",
                "host_name" : "hostname",
                "user_name" : "username123",
                "user_password" : "UserPassword123"
            },
            "source_image_name" : "0c5c79005aae478e8883bf950a861ce0__Windows-Server-2012-Essentials-20141204-enus",
            "network_config" : {
                "configuration_set_type" : "NetworkConfiguration",
                "input_endpoints" : [
                    {
                        "name" : "http",
                        "protocol" : "tcp",
                        "port" : "80",
                        "local_port" : "80"
                    },
                    {
                        "name" : "Deploy",
                        "protocol" : "tcp",
                        "port" : "3389",
                        "local_port" : "3389"
                    }
                ]
            },
            "role_size" : "Small",
            "remote": {
                "provider": "guacamole",
                "protocol": "rdp",
                "input_endpoint_name" : "Deploy"
            }
        }
    ]
}