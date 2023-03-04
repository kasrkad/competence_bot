# POST Create template
# Content-Type: application/json
# Authorization: Bearer {{token}}
TEMPLATE_ENDPOINT = "https://{jira_host}/rest/com.okapya.jira.checklist/latest/templates"

# GET
# Authorization: Bearer {{token}}
GET_PROJECT_TEMPLATES = "https://{jira_host}/rest/com.okapya.jira.checklist/latest/projects/15135/templates"

# GET/PUT
# Authorization: Bearer {{token}}
TEMPLATE_ID_ENDPOINT = "https://{jira_host}/rest/com.okapya.jira.checklist/latest/templates/{template_id}"

# GET
GET_ALL_PROJECTS = "https://{jira_host}/rest/api/2/project"
