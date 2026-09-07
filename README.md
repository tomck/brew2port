# brew2port

Conservative Homebrew → MacPorts migration planner for Intel and Apple-silicon Macs.

`brew2port` inventories only formulae installed on request (not dependency leaves) and installed casks, scores possible MacPorts equivalents, and produces a reviewable plan. It never removes Homebrew packages automatically. MacPorts installation is opt-in and each command is shown before execution.

For the Homebrew tap, use `brew tap tomck/escapefrombrewyork`; this repository contains the application source, while the tap formula lives in the `escapefrombrewyork` tap alongside `macpkgmap` and `brew2fink`.

The one-stop preparation workflow is `brew2port prepare`. It ensures MacPorts is present, refreshes its local PortIndex, inventories Homebrew, generates `migration-plan.json`, and writes `migration-preview.csv` for review. It does not install any migrated ports. After reviewing the CSV, run `brew2port migrate --plan migration-plan.json --install`; that command asks for confirmation, while `--yes` enables unattended execution.

If MacPorts is not installed, bootstrap it explicitly with `brew2port setup-macports`. This detects the macOS release, downloads the matching official installer, validates its checksum when the release provides one, validates the package signature, asks for administrator authorization, and verifies `/opt/local/bin/port` afterward. Use `--dry-run` to inspect the selected installer without changing the system, or `--skip-update` to omit the post-install `port selfupdate`.

To refresh an existing MacPorts installation independently, run `brew2port update-macports`. The equivalent plan option is `brew2port plan --inventory brew-inventory.json --update-macports`.

## Quick start

```sh
python3 -m brew2port inventory --output brew-inventory.json
python3 -m brew2port plan --inventory brew-inventory.json --output migration-plan.json
python3 -m brew2port plan --inventory brew-inventory.json --format text
python3 -m brew2port migrate --plan migration-plan.json --install
python3 -m brew2port verify --plan migration-plan.json
```

Without `--install`, `migrate` is a dry run. `--yes` is required for unattended installation. Homebrew is preserved; uninstalling it is deliberately outside this tool.

## Mapping data

`plan` queries the installed `macpkgmap` catalog client for each inventoried package. The client returns the catalog version, relationship type, confidence, review status, matching method, evidence, and source catalog versions; near-hits remain review-only. Anything not covered by the catalog falls back to the local MacPorts `PortIndex` when `port` is installed. Install the catalog client with `brew tap tomck/escapefrombrewyork && brew install macpkgmap`. The shared manager-neutral planning and safety primitives are provided by the `macpkg-migrate-core` package; brew2port does not require a checkout of the catalog repository and does not download the full catalog itself. The optional `--overrides FILE` flag accepts a curated override file when needed.

Catalog matching policy is owned by `macpkgmap`; generic character similarity is not package evidence, and uncertain or near-hit results require review. MacPorts target existence is checked against the local PortIndex before any installation command is run.

## Development

```sh
python3 -m unittest discover -s tests
python3 -m pip install .
```

The Homebrew formula is maintained in the dedicated `tomck/homebrew-escapefrombrewyork` tap; release archives should be built from a tagged commit and checksum-pinned there.

Sources: [Homebrew Formulae API](https://formulae.brew.sh/docs/api/), [Homebrew querying](https://docs.brew.sh/Querying-Brew), and [MacPorts port(1)](https://man.macports.org/port.1.html).
