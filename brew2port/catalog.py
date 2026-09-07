"""Thin subprocess client for the installed macpkgmap catalog command."""
import json
import subprocess

from macpkg_migrate_core import Identity, candidates_for, plan_record

INSTALL_HINT = "brew tap tomck/escapefrombrewyork\nbrew install macpkgmap"

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

def query(command, manager, package_type, name, run=subprocess.run):
    try:
        result=run([command,"relations",manager,package_type,name],capture_output=True,text=True,check=False)
    except FileNotFoundError as exc:
        raise RuntimeError("macpkgmap is required. Install it with:\n"+INSTALL_HINT) from exc
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or f"macpkgmap failed for {name}")
    return json.loads(result.stdout)

def definitions_for(items, command="macpkgmap", run=subprocess.run, progress=None):
    table={}; versions=set()
    for item in items:
        kind=item["kind"]; name=item["name"]
        response=query(command,"homebrew",kind,name,run=run)
        version=response.get("catalog_version");
        if version: versions.add(version)
        source=Identity("homebrew",kind,name)
        candidates=[candidate for candidate in candidates_for(response.get("results",[]),source)
                    if candidate.target.manager == "macports"
                    and candidate.relation_type not in {"no-equivalent", "conflicts"}]
        shared=plan_record(source,candidates,version,preference=("macports",))
        status=shared["recommendation"]["review_status"] if shared["recommendation"] else (candidates[0].review_status if candidates else "missing")
        table[(kind,name)]={"candidates":[candidate.as_dict() for candidate in candidates],"catalog_status":status,"catalog_version":version,"shared_record":shared}
        if progress: progress(f"Catalog lookup: {kind} {name}")
    table["catalog_version"]=(next(iter(versions)) if len(versions)==1 else ",".join(sorted(versions)))
    return table
