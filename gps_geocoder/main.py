"""
main.py — CLI entry point for gps-geocoder.

Commands:
    gps-geocoder geocode --lat LAT --lng LNG   Reverse geocode (maps → places → fallback)
    gps-geocoder init <map_id>                  Build a map database (e.g. tw, jp)
    gps-geocoder maps                           List installed/available maps
    gps-geocoder places import FILE             Import Google Takeout places
    gps-geocoder places list                    List saved places
    gps-geocoder places search KEYWORD          Search places by name
    gps-geocoder places near --lat LAT --lng Y  Find nearby places
    gps-geocoder latest [--name NAME]           Latest GPS + geocode (requires gps-bridge)
    gps-geocoder history [--limit N]            GPS history + geocode (requires gps-bridge)
"""

from __future__ import annotations

import json
import sys

import click

from gps_geocoder import __version__


@click.group()
@click.version_option(version=__version__, package_name="gps-geocoder")
def cli() -> None:
    """gps-geocoder — Offline map system with personal place markers."""


# ---------------------------------------------------------------------------
# geocode
# ---------------------------------------------------------------------------


@cli.command()
@click.option("--lat", required=True, type=float, help="Latitude")
@click.option("--lng", required=True, type=float, help="Longitude")
@click.option("--json", "as_json", is_flag=True, default=False, help="Output as JSON")
def geocode(lat: float, lng: float, as_json: bool) -> None:
    """Reverse geocode a coordinate (maps → places → fallback)."""
    from gps_geocoder.geocode import reverse_geocode

    result = reverse_geocode(lat, lng)

    if as_json:
        click.echo(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        source = result.get("source", "none")
        prefix = "" if source == "none" else f"[{source}] "
        click.echo(f"{prefix}{result['summary']}")


# ---------------------------------------------------------------------------
# init
# ---------------------------------------------------------------------------


@cli.command()
@click.argument("map_id")
@click.option("--force", is_flag=True, default=False, help="Re-download and rebuild.")
def init(map_id: str, force: bool) -> None:
    """Download and build a regional map database (e.g. tw, jp)."""
    from gps_geocoder.registry import get_map_build

    try:
        build_mod = get_map_build(map_id)
    except ImportError:
        click.echo(f"Map '{map_id}' is not installed.", err=True)
        click.echo("Install it with: pip install gps-geocoder[{map_id}]", err=True)
        sys.exit(1)

    build_mod.build_db(force=force)
    click.echo(f"\nMap '{map_id}' is ready.")


# ---------------------------------------------------------------------------
# maps
# ---------------------------------------------------------------------------


@cli.command()
@click.option("--json", "as_json", is_flag=True, default=False, help="Output as JSON")
def maps(as_json: bool) -> None:
    """List installed map plugins and their build status."""
    from gps_geocoder.registry import list_maps

    map_list = list_maps()

    if as_json:
        click.echo(json.dumps(map_list, ensure_ascii=False, indent=2))
        return

    if not map_list:
        click.echo("No map plugins installed.")
        click.echo("Install one with: pip install gps-geocoder[tw]")
        return

    for m in map_list:
        status = "built" if m["built"] else "not built"
        size = f"  {m['size_mb']} MB" if m["built"] else ""
        local = f" ({m['name_local']})" if m["name_local"] else ""
        mark = "+" if m["built"] else "-"
        click.echo(f"  {mark} {m['id']}  {m['name']}{local}  [{status}]{size}")


# ---------------------------------------------------------------------------
# places
# ---------------------------------------------------------------------------


@cli.group()
def places() -> None:
    """Manage personal place markers."""


@places.command("import")
@click.argument("filepath", type=click.Path(exists=True))
@click.option("--owner", default="", help="Owner name for multi-user support.")
def places_import(filepath: str, owner: str) -> None:
    """Import places from a Google Takeout GeoJSON file."""
    from gps_geocoder.places import import_google_takeout

    count = import_google_takeout(filepath, owner=owner)
    click.echo(f"Imported {count} places.")


@places.command("list")
@click.option("--owner", default=None, help="Filter by owner.")
@click.option("--category", default=None, type=click.Choice(["labeled", "saved"]), help="Filter by category.")
@click.option("--json", "as_json", is_flag=True, default=False, help="Output as JSON")
def places_list(owner: str | None, category: str | None, as_json: bool) -> None:
    """List all saved places."""
    from gps_geocoder.places import list_places

    results = list_places(owner=owner, category=category)

    if as_json:
        click.echo(json.dumps(results, ensure_ascii=False, indent=2))
        return

    if not results:
        click.echo("No places found.")
        return

    for p in results:
        owner_tag = f" [{p['owner']}]" if p["owner"] else ""
        cat = f" ({p['category']})" if p.get("category") else ""
        click.echo(f"  {p['name']}{owner_tag}{cat}  {p['lat']:.5f}, {p['lng']:.5f}")
        if p.get("address"):
            click.echo(f"    {p['address']}")


@places.command("search")
@click.argument("keyword")
@click.option("--owner", default=None, help="Filter by owner.")
@click.option("--json", "as_json", is_flag=True, default=False, help="Output as JSON")
def places_search(keyword: str, owner: str | None, as_json: bool) -> None:
    """Search places by name."""
    from gps_geocoder.places import search_places

    results = search_places(keyword, owner=owner)

    if as_json:
        click.echo(json.dumps(results, ensure_ascii=False, indent=2))
        return

    if not results:
        click.echo(f"No places matching '{keyword}'.")
        return

    for p in results:
        click.echo(f"  {p['name']}  {p['lat']:.5f}, {p['lng']:.5f}")
        if p.get("address"):
            click.echo(f"    {p['address']}")


@places.command("near")
@click.option("--lat", required=True, type=float, help="Latitude")
@click.option("--lng", required=True, type=float, help="Longitude")
@click.option("--radius", default=1000, type=int, help="Search radius in meters (default: 1000)")
@click.option("--owner", default=None, help="Filter by owner.")
@click.option("--json", "as_json", is_flag=True, default=False, help="Output as JSON")
def places_near(lat: float, lng: float, radius: int, owner: str | None, as_json: bool) -> None:
    """Find nearby saved places."""
    from gps_geocoder.places import near_places

    results = near_places(lat, lng, radius_m=radius, owner=owner)

    if as_json:
        click.echo(json.dumps(results, ensure_ascii=False, indent=2))
        return

    if not results:
        click.echo(f"No places within {radius}m.")
        return

    for p in results:
        click.echo(f"  {p['distance_m']:>6.0f}m  {p['name']}")
        if p.get("address"):
            click.echo(f"          {p['address']}")


# ---------------------------------------------------------------------------
# latest (requires gps-bridge)
# ---------------------------------------------------------------------------


@cli.command()
@click.option("--name", default=None, help="Tracker name.")
@click.option("--json", "as_json", is_flag=True, default=False, help="Output as JSON")
def latest(name: str | None, as_json: bool) -> None:
    """Show the latest GPS fix with reverse-geocoded location."""
    try:
        from gps_bridge.config import get_display_timezone
        from gps_bridge.storage import get_latest, init_db
    except ImportError:
        click.echo("This command requires gps-bridge. Install it with: pip install gps-bridge", err=True)
        sys.exit(1)
    from gps_geocoder.geocode import reverse_geocode

    init_db()
    record = get_latest(name=name)

    if record is None:
        click.echo("No GPS data found.")
        sys.exit(1)

    geo = reverse_geocode(record["lat"], record["lng"])
    result = {**record, "location": geo["summary"], "source": geo.get("source", "none")}

    if as_json:
        click.echo(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        from datetime import datetime
        from zoneinfo import ZoneInfo

        tz_name = get_display_timezone(lat=record["lat"], lng=record["lng"])
        try:
            dt = datetime.fromisoformat(record["received_at"])
            local = dt.astimezone(ZoneInfo(tz_name)).strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            local = record["received_at"]

        click.echo(f"  {local}  {result['location']}")
        click.echo(f"  lat: {record['lat']:.6f}, lng: {record['lng']:.6f}")


# ---------------------------------------------------------------------------
# history (requires gps-bridge)
# ---------------------------------------------------------------------------


@cli.command()
@click.option("--limit", default=10, show_default=True, type=click.IntRange(1, 1000))
@click.option("--name", default=None, help="Tracker name.")
@click.option("--since", default=None, help="Only records after this time (ISO-8601).")
@click.option("--until", default=None, help="Only records before this time (ISO-8601).")
@click.option("--json", "as_json", is_flag=True, default=False, help="Output as JSON")
def history(limit: int, name: str | None, since: str | None, until: str | None, as_json: bool) -> None:
    """Show GPS history with reverse-geocoded locations."""
    try:
        from gps_bridge.config import get_display_timezone
        from gps_bridge.storage import get_history, init_db
    except ImportError:
        click.echo("This command requires gps-bridge. Install it with: pip install gps-bridge", err=True)
        sys.exit(1)
    from gps_geocoder.geocode import reverse_geocode

    init_db()
    records = get_history(limit=limit, name=name, since=since, until=until)

    if not records:
        click.echo("No history records found.")
        return

    results = []
    for r in records:
        geo = reverse_geocode(r["lat"], r["lng"])
        results.append({**r, "location": geo["summary"], "source": geo.get("source", "none")})

    if as_json:
        click.echo(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        from datetime import datetime
        from zoneinfo import ZoneInfo

        for r in results:
            tz_name = get_display_timezone(lat=r["lat"], lng=r["lng"])
            try:
                dt = datetime.fromisoformat(r["received_at"])
                local = dt.astimezone(ZoneInfo(tz_name)).strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                local = r["received_at"]
            click.echo(f"  {local}  {r['location']}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    cli()
