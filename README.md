# brew2port

Conservative Homebrew → MacPorts migration planner for Intel and Apple-silicon Macs.

`brew2port` inventories only formulae installed on request (not dependency leaves) and installed casks, scores possible MacPorts equivalents, and produces a reviewable plan. It never removes Homebrew packages automatically. MacPorts installation is opt-in and each command is shown before execution.

For the Homebrew tap, use `brew tap tomck/brew2port`; the tap repository is named `homebrew-brew2port` as required by Homebrew, while the source project remains `brew2port`.

## Quick start

```sh
python3 -m brew2port inventory --output brew-inventory.json
python3 -m brew2port plan --inventory brew-inventory.json --ports macports-index.json --overrides overrides.json --output migration-plan.json
python3 -m brew2port plan --inventory brew-inventory.json --ports macports-index.json --format text
python3 -m brew2port migrate --plan migration-plan.json --install
python3 -m brew2port verify --plan migration-plan.json
```

Without `--install`, `migrate` is a dry run. `--yes` is required for unattended installation. Homebrew is preserved; uninstalling it is deliberately outside this tool.

## Mapping data

`build-index` downloads the documented Homebrew Formulae API (`formula.json`, `cask.json`) and accepts a local MacPorts export. A port index can be JSON (an array of objects with `name`, `description`, `homepage`, `provides`, `replaces`, `conflicts`, or `aliases`), TSV/CSV, or the line-oriented output of `port search --index`. Example override:

```json
{"muse-code": {"port": "muse_code", "confidence": 1.0, "reason": "curated"}, "foo": null}
```

`null` explicitly marks a package as no-match. Matching order is exact, normalized spelling, aliases/provides/replaces, token similarity, then curated overrides. Scores are evidence, not proof; ambiguous and low-confidence results require review.

## Development

```sh
python3 -m unittest discover -s tests
python3 -m pip install .
```

The Homebrew formula template is in `packaging/homebrew/brew2port.rb`; release archives should be built from a tagged commit and checksum-pinned there.

Sources: [Homebrew Formulae API](https://formulae.brew.sh/docs/api/), [Homebrew querying](https://docs.brew.sh/Querying-Brew), and [MacPorts port(1)](https://man.macports.org/port.1.html).
