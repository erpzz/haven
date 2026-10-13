# CERT-UA Early Warning Watch (civilian defensive use)

**Status:** offline analyzer and 24 total Python tests verified. Remote RSS fetching has NOT been validated from the test environment, which cannot resolve external DNS.

**Source:** official CERT-UA feed `https://cert.gov.ua/api/articles/rss` (verified by an external RSS reader). Uses public advisories, not live endpoints. No IP/host scanning, network operations against attackers, automatic blocking or exploit interactions.

## Run from project root

```shell
mkdir -p research/ukraine-civilian-cyber-defense/watch/output
python research/ukraine-civilian-cyber-defense/watch/cert_ua_watch.py --rss-file research/ukraine-civilian-cyber-defense/examples/sample-cert-ua.rss.xml --state research/ukraine-civilian-cyber-defense/watch/state.json --output-dir research/ukraine-civilian-cyber-defense/watch/output
python research/ukraine-civilian-cyber-defense/watch/cert_ua_watch.py --fetch --state research/ukraine-civilian-cyber-defense/watch/state.json --output-dir research/ukraine-civilian-cyber-defense/watch/output
python -m unittest discover -s research/ukraine-civilian-cyber-defense/tests -v
```

- The first successful run **baselines** existing advisories and never claims they were newly published.
- Subsequent runs write `latest_advisories.json`, `new_advisories.json`, and `defense_brief.md`.
- Malformed/nonofficial/empty feeds don't alter prior state. Validate the official RSS directly before relying on this.
- Keyword-derived suggestions are analyst review prompts, **not** confirmed detections or attribution.
- Only explicit `--fetch` retrieves the official advisory URL; other processing is offline.
- No victim data, external scanning, or credentials are required.

## Optional automated execution

A reviewable `.github/workflows/ukraine-certua-watch.yml` runs unit tests on PRs and, **if merged into the repository default branch and granted necessary Actions permissions**, is scheduled to fetch the official feed daily and commit changed public advisory summaries. It does not deploy protections. A pull request alone is not evidence that a scheduler has run.

## Defensive IOC review

The standalone `controls/review_indicators.py` accepts a *manually curated* local JSON array containing `type` (`domain` or `ipv4`), `indicator`, `source_url`, `confidence` (0–100), `approved` (true only after authorized analyst review), `approved_by` and `expires_utc` (UTC ISO 8601). It creates a CSV with `CANDIDATE` or `HOLD` decisions. It never uploads, tests, or installs firewall rules. A CANDIDATE still requires the defender's own change approval.

For example:

```sh
python research/ukraine-civilian-cyber-defense/controls/review_indicators.py indicators.json --output ioc-review.csv
```

**Never automatically block all addresses in a country, an ASN, or a cloud provider.**
