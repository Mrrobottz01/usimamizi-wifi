from django.core.management.base import BaseCommand
from django.db import transaction

from apps.entitlements.models import AccessEntitlement
from apps.hotspot_sessions.models import HotspotSession
from apps.radius.models import RadiusAccountingLog


class Command(BaseCommand):
    help = "Clean synthetic/test-generated RADIUS sessions and reset test entitlement metrics."

    def add_arguments(self, parser):
        parser.add_argument(
            '--session-id',
            type=str,
            default='test-session-001',
            help='Specific synthetic session ID to purge (default: test-session-001)',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        target_session_id = options['session_id']
        self.stdout.write(f"Purging synthetic test data for session: {target_session_id}")

        sessions_to_clean = HotspotSession.objects.filter(acct_session_id=target_session_id)
        affected_entitlement_ids = set(sessions_to_clean.values_list('entitlement_id', flat=True))

        deleted_sessions, _ = sessions_to_clean.delete()
        deleted_logs, _ = RadiusAccountingLog.objects.filter(session_id=target_session_id).delete()

        # Reset entitlement usage counters if corrupted by synthetic data
        for ent_id in affected_entitlement_ids:
            if ent_id:
                ent = AccessEntitlement.objects.filter(id=ent_id).first()
                if ent and ent.reference == 'ENT-20260902-03B6BE':
                    ent.usage_time_used_seconds = 0
                    ent.data_used_bytes = 0
                    ent.save(update_fields=['usage_time_used_seconds', 'data_used_bytes', 'updated_at'])
                    self.stdout.write(f"Reset counters for test entitlement: {ent.reference}")

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully purged {deleted_sessions} synthetic sessions and {deleted_logs} synthetic accounting logs."
            )
        )
