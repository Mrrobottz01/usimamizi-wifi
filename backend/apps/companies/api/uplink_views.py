from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import Company, RouterUplinkProfile
from ..services.uplink_services import (
    get_router_uplink_status,
    switch_router_uplink
)


def _get_target_company(request) -> Company:
    company_id = request.query_params.get('company_id') or request.data.get('company_id')
    if company_id:
        try:
            return Company.objects.get(id=company_id)
        except (Company.DoesNotExist, ValueError):
            pass
    company = Company.objects.filter(memberships__user=request.user, memberships__is_active=True).first()
    if not company:
        company = Company.objects.first()
    if not company:
        raise ValueError("No company found.")
    return company


class RouterUplinkStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            company = _get_target_company(request)
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        uplink_status = get_router_uplink_status()
        profiles = RouterUplinkProfile.objects.filter(company=company).order_by('-is_active', 'name')
        profiles_data = [
            {
                'id': str(p.id),
                'name': p.name,
                'ssid': p.ssid,
                'is_active': p.is_active,
                'created_at': p.created_at.isoformat(),
                'has_password': bool(p.password)
            }
            for p in profiles
        ]

        return Response({
            'status': uplink_status,
            'profiles': profiles_data
        })


class RouterUplinkConnectView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            company = _get_target_company(request)
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        profile_id = request.data.get('profile_id')
        ssid = request.data.get('ssid', '')
        password = request.data.get('password', '')
        profile_name = request.data.get('profile_name', '')

        if profile_id:
            try:
                saved_profile = RouterUplinkProfile.objects.get(id=profile_id, company=company)
                ssid = saved_profile.ssid
                password = saved_profile.password
                profile_name = saved_profile.name
            except RouterUplinkProfile.DoesNotExist:
                return Response({'detail': 'Saved profile not found.'}, status=status.HTTP_404_NOT_FOUND)

        if not ssid:
            return Response({'detail': 'SSID is required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            new_status = switch_router_uplink(
                company=company,
                ssid=ssid,
                password=password,
                profile_name=profile_name
            )
            return Response({
                'detail': f'Switched to network {ssid} successfully.',
                'status': new_status
            })
        except Exception as e:
            return Response({
                'detail': f'Failed to switch network: {str(e)}',
                'status': get_router_uplink_status()
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class RouterUplinkProfilesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            company = _get_target_company(request)
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        profiles = RouterUplinkProfile.objects.filter(company=company).order_by('-is_active', 'name')
        data = [
            {
                'id': str(p.id),
                'name': p.name,
                'ssid': p.ssid,
                'is_active': p.is_active,
                'created_at': p.created_at.isoformat(),
                'has_password': bool(p.password)
            }
            for p in profiles
        ]
        return Response(data)

    def post(self, request):
        try:
            company = _get_target_company(request)
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        ssid = request.data.get('ssid', '').strip()
        password = request.data.get('password', '').strip()
        name = request.data.get('name', '').strip() or ssid

        if not ssid:
            return Response({'detail': 'SSID is required.'}, status=status.HTTP_400_BAD_REQUEST)

        profile, created = RouterUplinkProfile.objects.update_or_create(
            company=company,
            ssid=ssid,
            defaults={
                'name': name,
                'password': password
            }
        )

        return Response({
            'id': str(profile.id),
            'name': profile.name,
            'ssid': profile.ssid,
            'is_active': profile.is_active,
            'created_at': profile.created_at.isoformat()
        }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    def delete(self, request, profile_id=None):
        try:
            company = _get_target_company(request)
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        target_id = profile_id or request.query_params.get('profile_id')
        if not target_id:
            return Response({'detail': 'profile_id is required.'}, status=status.HTTP_400_BAD_REQUEST)

        deleted_count, _ = RouterUplinkProfile.objects.filter(id=target_id, company=company).delete()
        if not deleted_count:
            return Response({'detail': 'Profile not found.'}, status=status.HTTP_404_NOT_FOUND)

        return Response({'detail': 'Profile deleted successfully.'})


class RouterUplinkScanView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from ..services.uplink_services import scan_nearby_networks
        try:
            networks = scan_nearby_networks()
            return Response(networks)
        except Exception as e:
            return Response({'detail': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class RouterUplinkRestoreHomeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        from ..services.uplink_services import restore_home_airtel
        try:
            company = _get_target_company(request)
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        try:
            new_status = restore_home_airtel(company=company)
            return Response({
                'detail': 'Restored connection to Home Airtel (Avie_5G) successfully.',
                'status': new_status
            })
        except Exception as e:
            return Response({'detail': f'Failed to restore Home Airtel: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

