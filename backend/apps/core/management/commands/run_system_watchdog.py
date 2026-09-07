import time
import sys
from django.core.management.base import BaseCommand
from apps.companies.models import Company
from apps.core.services.watchdog_services import run_full_watchdog_cycle


class Command(BaseCommand):
    help = "Monitors system infrastructure health (FreeRADIUS, Routers, Database) and sends SMS alerts upon outage."

    def add_arguments(self, parser):
        parser.add_argument(
            '--once',
            action='store_true',
            help='Run a single health check cycle and exit immediately (ideal for cron jobs).'
        )
        parser.add_argument(
            '--send-alerts',
            action='store_true',
            help='Enable real SMS alert dispatching when failures or recoveries are detected.'
        )
        parser.add_argument(
            '--interval',
            type=int,
            default=60,
            help='Loop interval in seconds when running as a daemon (default: 60s).'
        )
        parser.add_argument(
            '--company-id',
            type=str,
            default=None,
            help='Scope health checks to a specific company ID.'
        )

    def handle(self, *args, **options):
        run_once = options['once']
        send_alerts = options['send_alerts']
        interval = max(5, options['interval'])
        company_id = options['company_id']

        company = None
        if company_id:
            try:
                company = Company.objects.get(id=company_id)
            except Company.DoesNotExist:
                self.stderr.write(self.style.ERROR(f"Company '{company_id}' not found."))
                sys.exit(1)

        self.stdout.write(self.style.SUCCESS(
            f"=== Starting Usimamizi System Watchdog ===\n"
            f"Mode: {'Single cycle (--once)' if run_once else f'Daemon (interval: {interval}s)'}\n"
            f"SMS Alerts: {'ENABLED' if send_alerts else 'DISABLED (dry-run)'}\n"
            f"Scope: {company.name if company else 'Global Platform'}\n"
        ))

        while True:
            cycle_result = run_full_watchdog_cycle(company=company, send_alerts=send_alerts)
            
            timestamp = cycle_result['timestamp']
            overall = cycle_result['overall_status']
            probes = cycle_result['probes']

            status_style = self.style.SUCCESS if overall == 'HEALTHY' else self.style.ERROR
            self.stdout.write(f"\n[{timestamp}] Overall Health: {status_style(overall)}")

            any_down = False
            for p in probes:
                srv = str(p['service_name'])
                ident = str(p['service_identifier'])
                stat = str(p['status'])
                lat = p['latency_ms']
                err = p['error_message']

                if p['is_healthy']:
                    self.stdout.write(self.style.SUCCESS(f"  [OK]   {srv:15} | {ident:30} | {lat:6.1f}ms"))
                else:
                    any_down = True
                    self.stdout.write(self.style.ERROR(f"  [FAIL] {srv:15} | {ident:30} | {stat} - {err}"))

            if run_once:
                if any_down:
                    self.stdout.write(self.style.WARNING("Watchdog completed with one or more degraded/down services."))
                else:
                    self.stdout.write(self.style.SUCCESS("All monitored services are operating normally."))
                break

            time.sleep(interval)
