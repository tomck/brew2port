"""Thin subprocess client for the installed macpkgmap catalog command."""
import json
import subprocess
import urllib.request
from pathlib import Path

from macpkg_migrate_core import Identity, candidates_for, plan_record

INSTALL_HINT = "brew tap tomck/escapefrombrewyork\nbrew install macpkgmap"
DEFAULT_SNAPSHOT_URL = "https://tomck.github.io/macpkg-catalog/catalog.json"
DEFAULT_SNAPSHOT_CACHE = "~/.cache/brew2port/catalog.json"

def ensure_snapshot(path=DEFAULT_SNAPSHOT_CACHE, url=DEFAULT_SNAPSHOT_URL,
                    opener=urllib.request.urlopen, progress=None):
    """Return a validated local catalog snapshot, downloading it once if needed."""
    destination=Path(path).expanduser()
    if destination.exists():
        try:
            data=json.loads(destination.read_text())
            if isinstance(data,dict) and isinstance(data.get("relations"),list) and data.get("catalog_version"):
                if progress: progress(f"Using cached macpkgmap snapshot: {destination}")
                return destination
        except (OSError, json.JSONDecodeError):
            pass
        if progress: progress(f"Cached macpkgmap snapshot is invalid; refreshing: {destination}")
    if progress: progress(f"Downloading macpkgmap snapshot from {url}...")
    request=urllib.request.Request(url,headers={"User-Agent":"brew2port"})
    try:
        with opener(request) as response:
            data=json.loads(response.read().decode())
    except Exception as exc:
        raise RuntimeError(f"Unable to obtain macpkgmap catalog snapshot: {exc}") from exc
    if not isinstance(data,dict) or not isinstance(data.get("relations"),list) or not data.get("catalog_version"):
        raise RuntimeError("Published macpkgmap snapshot is invalid: expected catalog_version and relations")
    destination.parent.mkdir(parents=True,exist_ok=True)
    destination.write_text(json.dumps(data,separators=(",",":")))
    if progress: progress(f"Cached macpkgmap snapshot at {destination}")
    return destination

def load_catalog(path):
    """Compatibility loader for cached catalog files during transition."""
    data=json.loads(__import__('pathlib').Path(path).read_text())
    rows=data.get("relations",[]) if isinstance(data,dict) else data
    table={}
    for relation in rows:
        source=relation.get("source",{}); target=relation.get("target",{})
        if source.get("manager") != "homebrew" or target.get("manager") != "macports": continue
        key=("formula" if source.get("package_type")=="formula" else "cask",source.get("native_name"))
        table.setdefault(key,{"candidates":[],"catalog_status":relation.get("review_status","needs-review")})["candidates"].append({"port":target.get("native_name"),"confidence":relation.get("confidence",0),"reason":relation.get("matching_method","catalog"),"catalog_status":relation.get("review_status","needs-review")})
    return table

def query(command, manager, package_type, name, run=subprocess.run, snapshot=None):
    try:
        args=[command,"relations",manager,package_type,name]
        if snapshot: args.extend(["--snapshot",str(snapshot)])
        result=run(args,capture_output=True,text=True,check=False)
    except FileNotFoundError as exc:
        raise RuntimeError("macpkgmap is required. Install it with:\n"+INSTALL_HINT) from exc
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or f"macpkgmap failed for {name}")
    return json.loads(result.stdout)

def definitions_for(items, command="macpkgmap", run=subprocess.run, progress=None,
                    snapshot=None, snapshot_url=DEFAULT_SNAPSHOT_URL,
                    snapshot_opener=urllib.request.urlopen):
    table={}; versions=set()
    if snapshot:
        snapshot=ensure_snapshot(snapshot,snapshot_url,snapshot_opener,progress)
    for item in items:
        kind=item["kind"]; name=item["name"]
        response=query(command,"homebrew",kind,name,run=run,snapshot=snapshot)
        version=response.get("catalog_version");
        if version: versions.add(version)
        source=Identity("homebrew",kind,name)
        all_candidates=[candidate for candidate in candidates_for(response.get("results",[]),source)
                        if candidate.target.manager == "macports"]
        negative=any(candidate.relation_type in {"no-equivalent", "conflicts"} for candidate in all_candidates)
        candidates=[candidate for candidate in all_candidates
                    if candidate.relation_type not in {"no-equivalent", "conflicts"}]
        shared=plan_record(source,candidates,version,preference=("macports",))
        status=shared["recommendation"]["review_status"] if shared["recommendation"] else ("no-equivalent" if negative else (candidates[0].review_status if candidates else "missing"))
        table[(kind,name)]={"candidates":[candidate.as_dict() for candidate in candidates],"catalog_status":status,"catalog_version":version,"negative_relation":negative,"shared_record":shared}
        if progress: progress(f"Catalog lookup: {kind} {name}")
    table["catalog_version"]=(next(iter(versions)) if len(versions)==1 else ",".join(sorted(versions)))
    return table
