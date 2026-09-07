import logging
from django.conf import settings
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from ..services.radius_services import authorize_radius_access, process_radius_accounting
from .serializers import RadiusAccountingSerializer, RadiusAuthorizeSerializer

logger = logging.getLogger(__name__)


def validate_radius_api_key(request) -> bool:
    """
    Validate FreeRADIUS machine-to-machine API key if configured in settings.
    """
    configured_secret = getattr(settings, 'RADIUS_API_SECRET', None)
    if not configured_secret:
        return True

    auth_header = request.headers.get('X-RADIUS-API-KEY') or request.headers.get('Authorization')
    if not auth_header:
        return False

    if auth_header.startswith('Bearer '):
        token = auth_header.split('Bearer ', 1)[1].strip()
    else:
        token = auth_header.strip()

    return token == configured_secret


class RadiusAuthorizeView(APIView):
    """
    POST /api/v1/radius/authorize/
    FreeRADIUS rlm_rest module endpoint for Access-Request authorization decisions.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        if not validate_radius_api_key(request):
            return Response({"detail": "Invalid RADIUS API authorization key."}, status=status.HTTP_403_FORBIDDEN)

        serializer = RadiusAuthorizeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        result = authorize_radius_access(
            username=data['username'],
            password=data.get('password'),
            nas_ip=data.get('nas_ip'),
            nas_identifier=data.get('nas_identifier'),
            mac_address=data.get('mac_address')
        )
        logger.info(
            "RADIUS_AUTH_DECISION: username=%s nas_ip=%s accept=%s reason=%s reply=%s",
            data['username'], data.get('nas_ip'), result['accept'], result.get('reason'), result.get('reply')
        )

        if result['accept']:
            response_payload = {
                "control": {
                    "Auth-Type": "Accept"
                },
                "reply": result['reply'],
                "entitlement_id": result.get('entitlement_id'),
                "entitlement_reference": result.get('entitlement_reference')
            }
            # Expose reply attributes at top-level for FreeRADIUS rlm_rest JSON parser
            for k, v in result['reply'].items():
                response_payload[k] = v
            return Response(response_payload, status=status.HTTP_200_OK)
        else:
            reply_dict = result.get('reply', {"Reply-Message": "Access Denied."})
            response_payload = {
                "control": {
                    "Auth-Type": "Reject"
                },
                "reason": result.get('reason', 'REJECTED'),
                "reply": reply_dict
            }
            for k, v in reply_dict.items():
                response_payload[k] = v
            return Response(response_payload, status=status.HTTP_401_UNAUTHORIZED)


class RadiusAccountingView(APIView):
    """
    POST /api/v1/radius/accounting/
    FreeRADIUS rlm_rest module endpoint for processing Accounting packets (Start, Interim, Stop).
    """
    permission_classes = [AllowAny]

    def post(self, request):
        if not validate_radius_api_key(request):
            return Response({"detail": "Invalid RADIUS API authorization key."}, status=status.HTTP_403_FORBIDDEN)

        serializer = RadiusAccountingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        log_entry = process_radius_accounting(
            session_id=data['session_id'],
            username=data['username'],
            nas_ip=data['nas_ip'],
            nas_identifier=data.get('nas_identifier'),
            packet_type=data['packet_type'],
            mac_address=data.get('mac_address', ''),
            framed_ip=data.get('framed_ip'),
            input_octets=data.get('input_bytes', 0),
            output_octets=data.get('output_bytes', 0),
            input_gigawords=data.get('input_gigawords', 0),
            output_gigawords=data.get('output_gigawords', 0),
            session_time=data.get('session_time', 0),
            terminate_cause=data.get('terminate_cause', ''),
            raw_payload=request.data
        )

        return Response({
            "status": "success",
            "log_id": str(log_entry.id),
            "packet_type": log_entry.packet_type
        }, status=status.HTTP_200_OK)
