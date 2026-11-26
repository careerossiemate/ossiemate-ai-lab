# Package 11: platform foundations
Baseline 4248b9a. No new resources or inference during release.
- Authenticated usage dashboard: bounded personal metric scan and shared multimedia reservations. No actual cost feed; AUD 50 and AUD 5 are planning targets. Historical coverage incomplete. No automatic cost enforcement beyond existing quotas.
- Backend CI: compile and container build on GitHub. No Azure credentials or automatic cloud deployment. Existing consolidated ACR deployment and lifecycle retained.
- Bicep runtime reference: not deployed, not a complete infrastructure recreation; validate with Bicep and Azure what-if before use. Existing lifecycle remains authoritative.
- Read-only model and bot inventory during release, no secrets printed. Anonymous dashboard rejection included in smoke checks.
- Remaining native AG04, AG05, AG07, AG09 orchestration builder, AG10, LG05, VS05, VS08 semantic/indexer and 05 fine-tuning are not implemented by this release. Native Voice Live compatibility and video execution remain untested. Do not treat coverage as completion.
- GitHub OIDC and deployment approvals, actual billing integration, full IaC, consolidated functional testing and environment promotion remain outstanding.
