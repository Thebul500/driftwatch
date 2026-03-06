# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | Yes                |
| < 0.1   | No                 |

Only the latest minor release receives security patches. Users should always run the most recent version.

## Reporting a Vulnerability

If you discover a security vulnerability in driftwatch, please report it responsibly. **Do not open a public GitHub issue for security vulnerabilities.**

Instead, send an email to the project maintainers with the following information:

- Description of the vulnerability
- Steps to reproduce the issue
- Affected version(s)
- Any potential impact or exploit scenario

We will acknowledge receipt within 48 hours and aim to provide a fix or mitigation within 7 days for critical issues.

## Disclosure Policy

- We follow coordinated disclosure. Please allow up to 90 days before publicly disclosing a reported vulnerability.
- Once a fix is released, we will publish a security advisory in the repository.

## Security Considerations

Driftwatch handles infrastructure configuration data including Docker configs, crontabs, firewall rules, and package versions. Operators should:

- Run driftwatch behind a reverse proxy with TLS termination.
- Restrict API access to trusted networks or authenticated users.
- Protect the SQLite database file with appropriate filesystem permissions.
- Rotate JWT secrets regularly and use strong secret values.
- Review Signal alerting credentials and keep them out of version control.
