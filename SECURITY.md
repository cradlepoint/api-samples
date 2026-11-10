# Security Policy

## About this policy

This repository (`cradlepoint/api-samples`) contains sample and demonstration
scripts and web applications for interacting with the Ericsson Cradlepoint NetCloud
Manager (NCM) APIs. It is published as free and open-source software under Ericsson's
brand.

Ericsson acts as an **Open Source Software Steward** for this repository under the
EU Cyber Resilience Act (CRA). This policy documents how to report security issues,
what is in and out of scope, and the response you can expect.

## Scope

**In scope**

- The security and integrity of this repository itself: its contents, build/CI
  configuration (`.github/workflows/`), and the repository's GitHub configuration.
- The published release artifact: the `ncm` Python package on PyPI
  (<https://pypi.org/project/ncm/>), which is built and published automatically from
  the [`ncm/`](https://github.com/cradlepoint/api-samples/tree/master/ncm) directory
  by the
  [`ncm_pypi_package.yaml`](https://github.com/cradlepoint/api-samples/blob/master/.github/workflows/ncm_pypi_package.yaml)
  workflow.
- Vulnerabilities in the shared libraries and tooling maintained in this repository
  that are common to the samples — for example the `ncm/` SDK source, the shared
  helper utilities in `scripts/utils/` (credential handling, HTTP session setup,
  environment checks), and `setup_env.py`.
- Reports that a published artifact has been tampered with, that the PyPI publishing
  pipeline has been compromised, or that a contributor account or GitHub Action has
  been compromised.

**Out of scope**

- The behavior, correctness, or security of the individual sample scripts and
  applications under `scripts/`, `web_apps/`, `ncm_apiv1/`, `ncm_mcp_servers/`, and
  `ncm2/`. These are provided as **known-working examples**, not as supported
  products. Ericsson supports the platform (the NCM service and APIs) but does
  **not** support the individual sample code itself. See *What Ericsson supports*
  below.
- NetCloud Manager (NCM), the NCOS operating system, the NCM APIs, and Cradlepoint
  router hardware and firmware. These are commercial products with their own support
  and security reporting channels — see *Reporting a vulnerability in the platform*
  below.
- Vulnerabilities that exist only because a sample was modified, extended, or
  combined with other code after it was copied from this repository.
- Issues that depend on the user supplying their own API credentials insecurely
  (for example exposing a local dashboard with stored credentials on an untrusted
  network), which the repository documentation already warns against.

## What Ericsson supports

Ericsson supports the **platform**: the NetCloud Manager service and its APIs. The
sample scripts and web applications in this repository are provided as examples that
are known to work at the time of publication. The individual sample code is not sold
as a product and is not supported as one. Use it as a starting point, and review and
test it before using it against a production NCM tenant.

## Reporting a vulnerability

### A vulnerability in this repository (in scope)

Please report privately. **Do not open a public issue for a security vulnerability.**

- Use GitHub's **private vulnerability reporting**: go to the **Security** tab of this
  repository and click **Report a vulnerability**. This opens a private advisory
  visible only to you and the maintainers.

Please include:

- The affected file(s), release artifact, or configuration.
- A description of the issue and its potential impact.
- Steps to reproduce, a proof of concept, or a patch if you have one.
- Any relevant version, commit hash, release tag, or PyPI package version.

### A vulnerability in the platform (NCM, NCOS, hardware/firmware)

Vulnerabilities in Ericsson Cradlepoint products — as opposed to this sample
repository — should be reported to Ericsson's Product Security Incident Response Team
(PSIRT). See the PSIRT page for how to contact them and what to include:

- <https://www.ericsson.com/en/about-us/security/psirt>

If you are unsure whether an issue is in this repository or in the platform, report it
privately here and we will route it appropriately.

## Response expectations

> **Note:** The timeframes below are placeholders to be confirmed with Ericsson
> PSIRT / compliance before this policy is considered final.

As a Steward, Ericsson provides best-effort handling of in-scope reports:

- **Acknowledgement:** within 10 business days of receipt. *(placeholder — confirm with PSIRT/compliance)*
- **Initial assessment:** we will confirm whether the report is in scope and provide
  an initial severity assessment. *(target timeframe to be confirmed with PSIRT/compliance)*
- **Resolution:** for confirmed in-scope issues, we will work on a fix or mitigation
  and coordinate disclosure with you. Timelines depend on severity and complexity.

Reports that are out of scope (for example, issues in individual sample code or in
the platform) will be acknowledged and redirected to the appropriate channel rather
than fixed under this policy.

## Supported versions

Security maintenance applies only to the **latest** state of the `master` branch and
the most recently published version of the `ncm` package on PyPI
(<https://pypi.org/project/ncm/>). Older commits, tags, and previously published
package versions are **not** maintained. If you are running an older copy, update to
the latest version before reporting an issue.

## Coordinated disclosure

We ask that you give us a reasonable opportunity to investigate and remediate an
in-scope issue before any public disclosure. We will keep you informed of progress and
credit reporters who wish to be acknowledged.
