"""Quick lookup tool for the Tripletex API spec.

Usage:
  python lookup_api.py Employee              # show all fields + enums for a schema
  python lookup_api.py /employee post        # show POST params for an endpoint
  python lookup_api.py enums Employee        # show only enum fields
"""

import json
import sys

with open("tripletexapi.json") as f:
    spec = json.load(f)

schemas = spec["components"]["schemas"]
paths = spec["paths"]


def show_schema(name: str):
    if name not in schemas:
        print(f"Schema '{name}' not found.")
        print("Available:", [k for k in schemas if name.lower() in k.lower()])
        return
    s = schemas[name]
    required = s.get("required", [])
    props = s.get("properties", {})
    print(f"\n{name} (required: {required or 'none listed'})\n")
    for field, defn in props.items():
        typ = defn.get("type", defn.get("$ref", "object").split("/")[-1])
        enum = defn.get("enum")
        note = f"  enum={enum}" if enum else ""
        req = " *" if field in required else ""
        print(f"  {field}{req}: {typ}{note}")


def show_endpoint(path: str, method: str):
    if path not in paths:
        print(f"Path '{path}' not found.")
        return
    if method not in paths[path]:
        print(f"Method '{method}' not found. Available: {list(paths[path].keys())}")
        return
    op = paths[path][method]
    print(f"\n{method.upper()} {path}")
    print(f"Summary: {op.get('summary', '-')}")

    params = op.get("parameters", [])
    if params:
        print("\nQuery params:")
        for p in params:
            req = " *" if p.get("required") else ""
            print(f"  {p['name']}{req} ({p['in']})")

    body = op.get("requestBody", {})
    if body:
        for ct, ct_def in body.get("content", {}).items():
            schema = ct_def.get("schema", {})
            ref = schema.get("$ref", "")
            if ref:
                schema_name = ref.split("/")[-1]
                print(f"\nBody schema: {schema_name}")
                show_schema(schema_name)


def show_enums(name: str):
    if name not in schemas:
        print(f"Schema '{name}' not found.")
        return
    props = schemas[name].get("properties", {})
    found = {f: d["enum"] for f, d in props.items() if "enum" in d}
    if found:
        for field, values in found.items():
            print(f"{field}: {values}")
    else:
        print(f"No enum fields in {name}")


if len(sys.argv) < 2:
    print(__doc__)
    sys.exit(0)

arg1 = sys.argv[1]

if arg1 == "enums" and len(sys.argv) > 2:
    show_enums(sys.argv[2])
elif arg1.startswith("/"):
    method = sys.argv[2] if len(sys.argv) > 2 else "get"
    show_endpoint(arg1, method)
else:
    show_schema(arg1)
