from django.core.management.base import BaseCommand
from django.utils import timezone

from Weather_App.models import Location
from Weather_App.services import ForecastService, SOLAR_LOCATION_TO_PROVINCE


class Command(BaseCommand):
    help = "Refresh solar forecast (0-23h) into SolarForecast table. Deletes and recreates the day each run."

    def add_arguments(self, parser):
        parser.add_argument('--location-id', type=int, help='Refresh for a single location id')
        parser.add_argument('--all', action='store_true', help='Refresh for all supported locations (34 provinces)')
        parser.add_argument('--date', type=str, help='Target date YYYY-MM-DD (default: today)')
        parser.add_argument('--max-age-hours', type=float, default=1.0, help='Refresh if existing data older than this')

    def handle(self, *args, **options):
        location_id = options.get('location_id')
        refresh_all = options.get('all')
        date_str = options.get('date')
        max_age_hours = options.get('max_age_hours')

        if date_str:
            try:
                target_date = timezone.datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                raise SystemExit('Invalid --date format, expected YYYY-MM-DD')
        else:
            target_date = timezone.localdate()

        if not refresh_all and not location_id:
            raise SystemExit('Provide --location-id or --all')

        if refresh_all:
            locations = Location.objects.filter(id__in=SOLAR_LOCATION_TO_PROVINCE.keys()).order_by('id')
        else:
            locations = Location.objects.filter(id=location_id)

        ok = 0
        failed = 0
        for loc in locations:
            try:
                qs = ForecastService.get_or_refresh_solar_daily(loc, target_date=target_date, max_age_hours=max_age_hours)
                self.stdout.write(self.style.SUCCESS(f"Solar refreshed: {loc.id} {loc.city_name} ({qs.count()} rows)"))
                ok += 1
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Solar refresh failed: {loc.id} {loc.city_name}: {e}"))
                failed += 1

        self.stdout.write(self.style.SUCCESS(f"Done. ok={ok}, failed={failed}"))
