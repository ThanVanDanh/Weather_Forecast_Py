from __future__ import annotations

from datetime import datetime

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = (
        "Convert existing UTC-stored datetimes (from USE_TZ=True era) into VN local naive datetimes "
        "for projects switching to USE_TZ=False.\n\n"
        "This is mainly for SolarForecast/HourlyForecast forecast_time fields so they match CSV wall-clock times."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--models',
            default='solar,hourly',
            help='Comma-separated models to convert: solar,hourly (default: solar,hourly)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Print how many rows would change, without writing.',
        )

    def handle(self, *args, **options):
        if getattr(settings, 'USE_TZ', False):
            raise SystemExit('This command is intended for USE_TZ=False only. Set USE_TZ=False then rerun.')

        try:
            from zoneinfo import ZoneInfo
        except Exception as exc:
            raise SystemExit(f'zoneinfo not available: {exc}')

        from Weather_App.models import HourlyForecast, SolarForecast

        vn_tz = ZoneInfo(getattr(settings, 'TIME_ZONE', 'Asia/Ho_Chi_Minh'))
        utc_tz = ZoneInfo('UTC')

        selected = {m.strip().lower() for m in str(options['models']).split(',') if m.strip()}
        dry_run = bool(options['dry_run'])

        def to_local_naive_from_utc_naive(dt: datetime) -> datetime:
            # Treat stored naive datetime as UTC (how Django stored it under USE_TZ=True).
            if dt.tzinfo is not None:
                # If someone stored aware datetimes in DB, normalize to UTC then to VN.
                dt_utc = dt.astimezone(utc_tz)
            else:
                dt_utc = dt.replace(tzinfo=utc_tz)
            return dt_utc.astimezone(vn_tz).replace(tzinfo=None)

        total_updated = 0

        if 'solar' in selected:
            qs = SolarForecast.objects.all().only('id', 'forecast_time')
            rows = list(qs)
            for r in rows:
                r.forecast_time = to_local_naive_from_utc_naive(r.forecast_time)
            if dry_run:
                self.stdout.write(f'[dry-run] SolarForecast rows to update: {len(rows)}')
            else:
                SolarForecast.objects.bulk_update(rows, ['forecast_time'])
                self.stdout.write(f'Updated SolarForecast: {len(rows)} rows')
            total_updated += len(rows)

        if 'hourly' in selected:
            qs = HourlyForecast.objects.all().only('id', 'forecast_time')
            rows = list(qs)
            for r in rows:
                r.forecast_time = to_local_naive_from_utc_naive(r.forecast_time)
            if dry_run:
                self.stdout.write(f'[dry-run] HourlyForecast rows to update: {len(rows)}')
            else:
                HourlyForecast.objects.bulk_update(rows, ['forecast_time'])
                self.stdout.write(f'Updated HourlyForecast: {len(rows)} rows')
            total_updated += len(rows)

        self.stdout.write(self.style.SUCCESS(f'Done. total_rows={total_updated}, dry_run={dry_run}'))
