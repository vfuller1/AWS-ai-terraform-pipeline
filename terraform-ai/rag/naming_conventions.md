# AWS Naming Conventions

## General Rules
- Use lowercase letters, numbers, and hyphens only.
- Maximum length is 63 characters.
- Names must start with a letter.
- Avoid underscores and spaces.
- Keep descriptors concise and meaningful.

## Canonical Format
Use this format for most resources:

`{env}-{team}-{resource_type}-{descriptor}`

Examples:
- `prod-api-ec2-orders`
- `dev-data-s3-rawlogs`
- `stg-infra-vpc-core`

## Environment Codes
- `prod` = production
- `dev` = development
- `stg` = staging
- `mgmt` = shared management services

## Team Codes
- `api` = application API team
- `data` = data platform team
- `infra` = infrastructure team
- `sec` = security team
- `ops` = operations team

## EC2 Pattern
Pattern:

`{env}-{team}-ec2-{workload}`

Guidance:
- Workload should map to app/service name.
- Include role hints only when needed (`web`, `worker`, `batch`).

## S3 Pattern
Pattern:

`{env}-{team}-s3-{dataset}`

Guidance:
- Dataset or function should be clear (`artifacts`, `backups`, `rawlogs`).
- Ensure global uniqueness with short suffix if needed.

## VPC Pattern
Pattern:

`{env}-{team}-vpc-{zone}`

Guidance:
- Use `core`, `shared`, or region hints as descriptor.
- Keep VPC names stable over time.

## Security Group Pattern
Pattern:

`{env}-{team}-sg-{purpose}`

Guidance:
- Purpose should match traffic intent (`web-ingress`, `db-egress`).

## IAM Role Pattern
Pattern:

`{env}-{team}-iam-{purpose}`

Guidance:
- Purpose should reflect trust boundary or workload.

## Subnet Pattern
Pattern:

`{env}-{team}-subnet-{scope}`

Guidance:
- Use `public-a`, `private-a`, `private-b` style descriptors.

## Required Tags
Every managed resource must include these tags:
- `Name`
- `Owner`
- `CreatedDate`
- `ManagedBy`
- `Environment`
