# Upstream intake

This directory tracks recurring review of `LPFchan/repo-template` changes as repository-development input. The template is a structural reference, not an authority over `neo`.

## Intake decisions

Each reviewed upstream change should be classified as one of:

- Adopt: bring the idea in with minimal local adaptation.
- Adapt: use the idea but change it for `neo` runtime and repository contracts.
- Defer: leave for later because prerequisites or need are unclear.
- Reject: do not bring it in because it conflicts with local contracts or scope.

## Files

- [`known-local-overrides.md`](known-local-overrides.md): standing differences from repo-template that reviewers should preserve.
- [`compatibility-watchlist.md`](compatibility-watchlist.md): upstream areas that may require careful review in future.
- [`reports/`](reports/): dated or PR-scoped intake reports when a concrete upstream review is performed.
