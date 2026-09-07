"""Thin subprocess client for the installed macpkgmap catalog command."""
import json
import subprocess

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
        relations=response.get("results",[])
        candidates=[]; status="missing"
        for relation in relations:
            target=relation.get("target",{}); status=relation.get("review_status", "needs-review")
            if target.get("manager") != "macports": continue
            candidates.append({"port":target.get("native_name"),"confidence":relation.get("confidence",0),"reason":relation.get("matching_method","catalog"),"catalog_status":status})
        table[(kind,name)]={"candidates":sorted(candidates,key=lambda x:x.get("confidence",0),reverse=True),"catalog_status":status,"catalog_version":version}
        if progress: progress(f"Catalog lookup: {kind} {name}")
    table["catalog_version"]=(next(iter(versions)) if len(versions)==1 else ",".join(sorted(versions)))
    return table
