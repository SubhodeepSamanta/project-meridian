# Repository structure

## Proposed top-level layout

~~~text
project-meridian/
├── documentations/
├── apps/
│   ├── api/
│   │   ├── app/
│   │   │   ├── api/
│   │   │   │   └── routes/
│   │   │   ├── core/
│   │   │   ├── db/
│   │   │   ├── domain/
│   │   │   │   ├── identities/
│   │   │   │   ├── certificates/
│   │   │   │   ├── policies/
│   │   │   │   ├── incidents/
│   │   │   │   └── audit/
│   │   │   ├── integrations/
│   │   │   │   ├── step_ca.py
│   │   │   │   └── pkcs11.py
│   │   │   ├── services/
│   │   │   └── main.py
│   │   └── tests/
│   └── web/
│       ├── src/
│       │   ├── app/
│       │   ├── components/
│       │   ├── features/
│       │   │   ├── identities/
│       │   │   ├── certificates/
│       │   │   ├── incidents/
│       │   │   └── audit/
│       │   ├── lib/
│       │   ├── pages/
│       │   └── styles/
│       └── tests/
├── infrastructure/
│   ├── docker/
│   ├── step-ca/
│   └── softhsm/
├── simulators/
│   ├── services/
│   └── agents/
├── scripts/
├── .env.example
├── .gitignore
├── docker-compose.yml
└── README.md
~~~

## Naming rules

- use lowercase folder and file names
- use hyphens only for documentation names
- use snake_case for Python modules
- use PascalCase for React components
- use clear domain names such as certificates, identities, incidents, and audit
- avoid vague names such as helpers, misc, common, stuff, or temp
- use singular class names and plural feature folders
- use descriptive test names that state the behavior

## Code ownership by area

- API routes translate HTTP requests into domain operations.
- Domain modules contain business rules.
- Integration modules talk to external tools.
- The dashboard calls the API and does not contain security decisions.
- Simulators perform demonstrations but do not bypass the API.
- Scripts set up and reset the local lab.

## Secrets and generated files

Never commit:

- private keys
- SoftHSM token files
- CA database files
- local environment files
- generated certificates
- Docker volumes
- logs containing sensitive material

Use .env.example for names and safe placeholder values. Use .gitignore before generating local credentials.
