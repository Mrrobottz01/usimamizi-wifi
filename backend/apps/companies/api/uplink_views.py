from typing import Optional
from django.db import models
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.routers.models import Router
from ..models import Company, RouterUplinkProfile
from ..services.uplink_services import (
    get_router_uplink_status,
    switch_router_uplink,
    scan_nearby_networks,
    restore_home_airtel
)


def _get_target_company(request) -> Company:
    query_params = getattr(request, 'query_params', getattr(request, 'GET', {}))
    data = getattr(request, 'data', getattr(request, 'POST', {}))
    company_id = query_params.get('company_id') or (
        data.get('company_id') if isinstance(data, dict) else None
    )
    if company_id:
        try:
            return Company.objects.get(id=company_id)
        except (Company.DoesNotExist, ValueError):
            pass
    company = Company.objects.filter(memberships__user=getattr(request, 'user', None), memberships__is_active=True).first()
    if not company:
        company = Company.objects.first()
    if not company:
        raise ValueError("No company found.")
    return company


def _resolve_target_router(request, company: Company) -> Optional[Router]:
    """
    Resolve the specific router targeted by this uplink management request.
    Inspects query params and request body for router_id or router_ip.
    Falls back gracefully to the company's active ONLINE router or configured router.
    """
    query_params = getattr(request, 'query_params', getattr(request, 'GET', {}))
    data = getattr(request, 'data', getattr(request, 'POST', {}))

    router_id = query_params.get('router_id') or (
        data.get('router_id') if isinstance(data, dict) else None
    )
    router_ip = query_params.get('router_ip') or (
        data.get('router_ip') if isinstance(data, dict) else None
    )

    if router_id:
        router = Router.objects.filter(id=router_id, company=company).first()
        if router:
            return router

    if router_ip:
        router = Router.objects.filter(management_ip=router_ip, company=company).first()
        if router:
            return router

    # Fallback 1: Router with status ONLINE
    online_router = company.routers.filter(is_active=True, health_status='ONLINE').first()
    if online_router:
        return online_router

    # Fallback 2: Router with credentials configured
    with_creds = company.routers.filter(is_active=True, has_credentials=True).first()
    if with_creds:
        return with_creds

    # Fallback 3: Most recently updated active router
    return company.routers.filter(is_active=True).order_by('-updated_at').first()


class RouterUplinkStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            company = _get_target_company(request)
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        target_router = _resolve_target_router(request, company)
        uplink_status = get_router_uplink_status(router=target_router, company=company)

        profile_filter = models.Q(company=company)
        if target_router:
            profile_filter &= (models.Q(router=target_router) | models.Q(router__isnull=True))
        profiles = RouterUplinkProfile.objects.filter(profile_filter).order_by('-is_active', 'name')
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

        target_router = _resolve_target_router(request, company)
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
                profile_name=profile_name,
                router=target_router,
            )
            return Response({
                'detail': f'Switched to network {ssid} successfully.',
                'status': new_status
            })
        except Exception as e:
            err_msg = str(e)
            current_status = get_router_uplink_status(router=target_router, company=company)
            is_transient = any(phrase in err_msg.lower() for phrase in ['timed out', 'connection refused', 'host unreachable'])
            if is_transient:
                current_status['ssid'] = ssid
                current_status['signal_strength'] = 'Associating...'
                return Response({
                    'detail': f'Switched uplink to {ssid}. Reconnecting...',
                    'status': current_status
                }, status=status.HTTP_200_OK)

            return Response({
                'detail': f'Failed to switch network: {err_msg}',
                'status': current_status
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class RouterUplinkProfilesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            company = _get_target_company(request)
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        target_router = _resolve_target_router(request, company)
        profile_filter = models.Q(company=company)
        if target_router:
            profile_filter &= (models.Q(router=target_router) | models.Q(router__isnull=True))
        profiles = RouterUplinkProfile.objects.filter(profile_filter).order_by('-is_active', 'name')
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

        target_router = _resolve_target_router(request, company)
        ssid = request.data.get('ssid', '').strip()
        password = request.data.get('password', '').strip()
        name = request.data.get('name', '').strip() or ssid

        if not ssid:
            return Response({'detail': 'SSID is required.'}, status=status.HTTP_400_BAD_REQUEST)

        lookup_kwargs = {'company': company, 'ssid': ssid}
        if target_router:
            lookup_kwargs['router'] = target_router

        profile, created = RouterUplinkProfile.objects.update_or_create(
            **lookup_kwargs,
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
        try:
            company = _get_target_company(request)
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        target_router = _resolve_target_router(request, company)
        try:
            networks = scan_nearby_networks(router=target_router)
            return Response(networks)
        except Exception as e:
            return Response({'detail': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class RouterUplinkRestoreHomeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            company = _get_target_company(request)
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        target_router = _resolve_target_router(request, company)
        try:
            new_status = restore_home_airtel(company=company, router=target_router)
            return Response({
                'detail': 'Restored connection to Home Airtel (Avie_5G) successfully.',
                'status': new_status
            })
        except Exception as e:
            return Response({'detail': f'Failed to restore Home Airtel: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

