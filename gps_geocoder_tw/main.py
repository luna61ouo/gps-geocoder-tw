"""
main.py — CLI entry point for gps-geocoder-tw.

Commands:
    gps-geocoder init                          Download Taiwan OSM data and build database.
    gps-geocoder geocode --lat LAT --lng LNG   Reverse geocode a single coordinate.
    gps-geocoder history [--limit N] [--name N] Show GPS history with location names.
    gps-geocoder latest [--name NAME]          Show latest GPS fix with location name.
"""

from __future__ import annotations

import json
import sys

import click

from gps_geocoder_tw import __version__


@click.group()
@click.version_option(version=__version__, package_name="gps-geocoder-tw")
def cli() -> None:
    """gps-geocoder-tw — Offline reverse geocoder for Taiwan GPS coordinates."""


# ---------------------------------------------------------------------------
# init
# ---------------------------------------------------------------------------


@cli.command()
@click.option("--force", is_flag=True, default=False, help="Re-download and rebuild even if data exists.")
def init(force: bool) -> None:
    """Download Taiwan OSM data and build the geocoder database."""
    from gps_geocoder_tw.build import build_db

    build_db(force=force)
    click.echo("\nReady! You can now use `gps-geocoder geocode` or `gps-geocoder history`.")


# ---------------------------------------------------------------------------
# geocode
# ---------------------------------------------------------------------------


@cli.command()
@click.option("--lat", required=True, type=float, help="Latitude")
@click.option("--lng", required=True, type=float, help="Longitude")
@click.option("--json", "as_json", is_flag=True, default=False, help="Output as JSON")
def geocode(lat: float, lng: float, as_json: bool) -> None:
    """Reverse geocode a single GPS coordinate."""
    from gps_geocoder_tw.query import reverse_geocode

    result = reverse_geocode(lat, lng)

    if as_json:
        click.echo(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        click.echo(result["summary"])


# ---------------------------------------------------------------------------
# history
# ---------------------------------------------------------------------------


@cli.command()
@click.option("--limit", default=10, show_default=True, type=click.IntRange(1, 1000),
              help="Number of recent records.")
@click.option("--name", default=None, help="Tracker name.")
@click.option("--since", default=None, help="Only records after this time (ISO-8601).")
@click.option("--until", default=None, help="Only records before this time (ISO-8601).")
@click.option("--json", "as_json", is_flag=True, default=False, help="Output as JSON")
def history(limit: int, name: str | None, since: str | None, until: str | None, as_json: bool) -> None:
    """Show GPS history with reverse-geocoded location names."""
    try:
        from gps_bridge.config import get_display_timezone
        from gps_bridge.storage import get_history, init_db
    except ImportError:
        click.echo("This command requires gps-bridge. Install it with: pip install gps-bridge", err=True)
        sys.exit(1)
    from gps_geocoder_tw.query import reverse_geocode

    init_db()
    records = get_history(limit=limit, name=name, since=since, until=until)

    if not records:
        click.echo("No history records found.")
        return

    results = []
    for r in records:
        geo = reverse_geocode(r["lat"], r["lng"])
        entry = {
            **r,
            "location": geo["summary"],
            "city": geo["city"],
            "district": geo["district"],
            "street": geo["street"],
            "poi": geo["poi"],
        }
        results.append(entry)

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
# latest
# ---------------------------------------------------------------------------


@cli.command()
@click.option("--name", default=None, help="Tracker name.")
@click.option("--json", "as_json", is_flag=True, default=False, help="Output as JSON")
def latest(name: str | None, as_json: bool) -> None:
    """Show the latest GPS fix with reverse-geocoded location name."""
    try:
        from gps_bridge.config import get_display_timezone
        from gps_bridge.storage import get_latest, init_db
    except ImportError:
        click.echo("This command requires gps-bridge. Install it with: pip install gps-bridge", err=True)
        sys.exit(1)
    from gps_geocoder_tw.query import reverse_geocode

    init_db()
    record = get_latest(name=name)

    if record is None:
        click.echo("No GPS data found.")
        sys.exit(1)

    geo = reverse_geocode(record["lat"], record["lng"])
    result = {
        **record,
        "location": geo["summary"],
        "city": geo["city"],
        "district": geo["district"],
        "street": geo["street"],
        "poi": geo["poi"],
    }

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
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    cli()
