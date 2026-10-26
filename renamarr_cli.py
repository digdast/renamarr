#!/usr/bin/env python3
"""
Renamarr Remote CLI & Headless Automation Client
Enables scanning, renaming, and batch undo from any remote terminal, cron job, or script.
"""
import os
import sys
import argparse
import urllib.request
import urllib.parse
import json

def api_call(endpoint: str, method: str = "GET", payload: dict = None, host: str = "http://localhost:7879"):
    url = f"{host.rstrip('/')}{endpoint}"
    headers = {"Content-Type": "application/json", "User-Agent": "Renamarr-CLI/1.0"}
    
    data = json.dumps(payload).encode('utf-8') if payload else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        err_body = e.read().decode('utf-8')
        try:
            return json.loads(err_body)
        except:
            return {"success": False, "error": f"HTTP {e.code}: {err_body}"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def cmd_status(args):
    res = api_call("/api/system/network", host=args.remote)
    if "hostname" in res:
        print(f"Renamarr Host: {res.get('hostname')}")
        print("Available Remote Endpoints:")
        for u in res.get("remote_urls", []):
            print(f"  -> {u}")
    else:
        print(f"Status check failed: {res.get('error')}")

def cmd_scan(args):
    print(f"[*] Scanning path '{args.path}' on Renamarr ({args.remote})...")
    payload = {
        "path": args.path,
        "recursive": not args.no_recursive,
        "organize_folders": not args.no_folders
    }
    res = api_call("/api/scan", method="POST", payload=payload, host=args.remote)
    if not res.get("success"):
        print(f"[!] Scan Error: {res.get('error')}")
        sys.exit(1)

    items = res.get("items", [])
    if args.json:
        print(json.dumps(items, indent=2))
        return

    print(f"\nFound {len(items)} media file(s):\n")
    print(f"{'Type':<10} {'Original File':<35} {'-->'} {'Target Filename'}")
    print("-" * 90)
    for it in items:
        mtype = it.get("media_type", "Movie")
        orig = it.get("original_filename", "")[:33]
        target = it.get("target_filename", "")
        print(f"{mtype:<10} {orig:<35} {'-->'} {target}")
    print("-" * 90)

def cmd_rename(args):
    # Step 1: Scan first to retrieve targets
    print(f"[*] Analyzing '{args.path}' before rename...")
    payload = {
        "path": args.path,
        "recursive": not args.no_recursive,
        "organize_folders": not args.no_folders
    }
    scan_res = api_call("/api/scan", method="POST", payload=payload, host=args.remote)
    if not scan_res.get("success"):
        print(f"[!] Scan failed: {scan_res.get('error')}")
        sys.exit(1)

    items = scan_res.get("items", [])
    actionable = [it for it in items if not it.get("is_already_named")]
    if not actionable:
        print("[✓] All files are already compliant with Plex naming standards. No renames required.")
        return

    print(f"\n[!] {len(actionable)} file(s) pending rename:\n")
    for it in actionable:
        print(f"  • {it['original_filename']}")
        print(f"    --> {it['target_path']}\n")

    if not args.yes:
        confirm = input("Proceed with renaming? (y/N): ").strip().lower()
        if confirm != "y":
            print("Aborted.")
            return

    rename_payload = {
        "items": [{"original_path": it["original_path"], "target_path": it["target_path"]} for it in actionable],
        "dry_run": args.dry_run
    }
    res = api_call("/api/rename", method="POST", payload=rename_payload, host=args.remote)
    if res.get("success"):
        renamed = res.get("result", {}).get("renamed_count", 0)
        print(f"\n[✓] Successfully renamed {renamed} file(s)!")
    else:
        print(f"[!] Rename error: {res.get('error')}")

def cmd_undo(args):
    print(f"[*] Requesting batch undo from {args.remote}...")
    res = api_call("/api/undo", method="POST", host=args.remote)
    if res.get("success"):
        print(f"[✓] Undo successful! Reverted {res.get('reverted_count')} file(s).")
    else:
        print(f"[!] Undo message: {res.get('message', res.get('error'))}")

def main():
    parser = argparse.ArgumentParser(description="Renamarr Remote CLI & Automation Client")
    parser.add_argument("--remote", default=os.getenv("RENAMARR_HOST", "http://localhost:7879"),
                        help="Remote Renamarr server URL (e.g. http://192.168.0.25:7879)")
    
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    # status
    p_status = subparsers.add_parser("status", help="Check remote Renamarr connectivity")
    p_status.set_defaults(func=cmd_status)

    # scan
    p_scan = subparsers.add_parser("scan", help="Scan directory and show proposed renames")
    p_scan.add_argument("--path", required=True, help="Directory path or UNC network share to scan")
    p_scan.add_argument("--no-recursive", action="store_true", help="Disable recursive subfolder scan")
    p_scan.add_argument("--no-folders", action="store_true", help="Do not create Season/Movie folders")
    p_scan.add_argument("--json", action="store_true", help="Output raw JSON")
    p_scan.set_defaults(func=cmd_scan)

    # rename
    p_rename = subparsers.add_parser("rename", help="Execute batch renames on target path")
    p_rename.add_argument("--path", required=True, help="Directory path or UNC network share to rename")
    p_rename.add_argument("--no-recursive", action="store_true", help="Disable recursive subfolder scan")
    p_rename.add_argument("--no-folders", action="store_true", help="Do not create Season/Movie folders")
    p_rename.add_argument("--yes", "-y", action="store_true", help="Skip confirmation prompt")
    p_rename.add_argument("--dry-run", action="store_true", help="Simulate without touching filesystem")
    p_rename.set_defaults(func=cmd_rename)

    # undo
    p_undo = subparsers.add_parser("undo", help="Revert the latest batch rename operation")
    p_undo.set_defaults(func=cmd_undo)

    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()
