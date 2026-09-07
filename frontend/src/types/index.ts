export type Theme = 'light' | 'dark' | 'system';

export interface User {
  id: string;
  email: string;
  phone: string;
  first_name: string;
  last_name: string;
  full_name: string;
  is_active: boolean;
  is_staff: boolean;
  created_at: string;
}

export interface Company {
  id: string;
  name: string;
  slug: string;
  legal_name?: string;
  phone?: string;
  email?: string;
  country: string;
  currency: string;
  timezone: string;
  status: 'TRIAL' | 'ACTIVE' | 'SUSPENDED' | 'CANCELLED';
  created_at: string;
  updated_at: string;
}

export interface ApiError {
  code: string;
  detail: string;
  field_errors?: Record<string, string[] | string>;
}

export interface Plan {
  id: string;
  company_id: string;
  name: string;
  code: string;
  description: string;
  price: string;
  currency: string;
  duration_value: number;
  duration_unit: 'MINUTES' | 'HOURS' | 'DAYS' | 'WEEKS' | 'MONTHS';
  duration_unit_display: string;
  validity_mode: 'CONTINUOUS' | 'USAGE_TIME' | 'CALENDAR';
  validity_mode_display: string;
  download_speed_kbps?: number;
  upload_speed_kbps?: number;
  data_limit_bytes?: number;
  max_devices: number;
  simultaneous_sessions: number;
  idle_timeout_seconds?: number;
  session_timeout_seconds?: number;
  is_active: boolean;
  sort_order: number;
  created_at: string;
  updated_at: string;
}

export interface VoucherBatch {
  id: string;
  company_id: string;
  plan: Plan;
  reference: string;
  label: string;
  notes?: string;
  distribution_mode?: 'CENTRAL_SAAS' | 'LOCAL_FALLBACK';
  export_status?: 'NOT_EXPORTED' | 'EXPORTED_ROUTEROS';
  quantity: number;
  expires_at?: string;
  created_by_email: string;
  available_count: number;
  reserved_count?: number;
  redeemed_count: number;
  revoked_count: number;
  expired_count: number;
  created_at: string;
  updated_at: string;
}

export interface Voucher {
  id: string;
  company_id: string;
  batch_id: string;
  batch_reference: string;
  plan_id: string;
  plan_name: string;
  plan_code: string;
  display_code: string;
  status: 'AVAILABLE' | 'RESERVED' | 'REDEEMED' | 'EXPIRED' | 'REVOKED';
  distribution_state: 'UNSOLD' | 'SOLD' | 'GIVEN_FREE' | 'PROMOTIONAL' | 'INTERNAL_TEST';
  export_status: 'NOT_EXPORTED' | 'EXPORTED_ROUTEROS';
  recipient_phone: string;
  expires_at?: string;
  reserved_at?: string;
  redeemed_at?: string;
  redeemed_by_customer: string;
  revoked_at?: string;
  revocation_reason: string;
  created_at: string;
  updated_at: string;
}

export interface VoucherMetrics {
  total: number;
  available: number;
  reserved: number;
  redeemed: number;
  expired: number;
  revoked: number;
  sent_sms: number;
  exported_routeros: number;
  sold: number;
  unsold: number;
  free: number;
  redemption_rate: number;
}

export interface VoucherTimelineEvent {
  event: string;
  timestamp: string;
  title: string;
  description: string;
  status: 'success' | 'info' | 'warning' | 'error';
}

export interface PrintableVoucherCard {
  id: string;
  code: string;
  plan_name: string;
  plan_code: string;
  price: string;
  currency: string;
  duration_display: string;
  speed_display: string;
  quota_display: string;
  devices: number;
  ssid: string;
  portal_url: string;
  qr_url: string;
  batch_ref: string;
  expires_at?: string;
}

export interface SMSProviderSenderID {
  id: string;
  sender_id: string;
  external_id?: string;
  display_name?: string;
  status: string;
  is_available: boolean;
  is_default: boolean;
  last_synced_at: string;
}

export interface NotificationProviderConfig {
  id: string;
  name: string;
  code: string;
  provider_type: 'BEEM' | 'NEXTSMS' | 'RAFIKISMS' | 'MOCK';
  channel: string;
  priority: number;
  is_active: boolean;
  base_url: string;
  sender_id: string;
  default_sender_id?: string;
  supports_delivery_receipts: boolean;
  last_sender_sync_at?: string;
  available_sender_ids?: SMSProviderSenderID[];
  sender_ids_count?: number;
  created_at: string;
  updated_at: string;
}

export interface SMSDeliveryAttempt {
  id: string;
  provider_code: string;
  sender_id: string;
  attempt_number: number;
  status: 'PENDING' | 'SUCCESS' | 'FAILED';
  provider_reference: string;
  provider_status: string;
  failure_category?: string;
  failure_code?: string;
  failure_reason?: string;
  started_at: string;
  completed_at?: string;
}

export interface SMSHistoryItem {
  id: string;
  recipient_masked: string;
  recipient: string;
  phone_normalized: string;
  channel: string;
  message_type: string;
  status: 'QUEUED' | 'SENDING' | 'SENT' | 'DELIVERED' | 'FAILED';
  provider_used: string;
  sender_id: string;
  attempt_count: number;
  provider_reference: string;
  voucher_id?: string;
  voucher_code?: string;
  voucher_batch_id?: string;
  plan_name?: string;
  created_at: string;
  sent_at?: string;
  delivered_at?: string;
  failed_at?: string;
}

export interface SMSHistoryDetail extends SMSHistoryItem {
  rendered_content: string;
  queued_at?: string;
  can_retry: boolean;
  attempts: SMSDeliveryAttempt[];
}

export interface SMSHistorySummary {
  total_messages: number;
  delivered: number;
  sent: number;
  failed: number;
  queued: number;
  sending: number;
  delivery_rate: number | null;
}

export type EntitlementStatus = 'PENDING' | 'ACTIVE' | 'SUSPENDED' | 'EXPIRED' | 'REVOKED';
export type EntitlementSourceType = 'VOUCHER' | 'MANUAL' | 'PAYMENT' | 'PROMOTION' | 'ADMIN';

export interface AccessEntitlement {
  id: string;
  reference: string;
  status: EntitlementStatus;
  source_type: EntitlementSourceType;
  plan_id: string;
  plan_name: string;
  plan_code: string;
  voucher_id?: string;
  voucher_code?: string;
  customer_email?: string;
  activated_at?: string;
  valid_from?: string;
  expires_at?: string;
  validity_mode: string;
  download_speed_kbps?: number;
  upload_speed_kbps?: number;
  data_limit_bytes?: number;
  data_used_bytes: number;
  remaining_data_bytes?: number;
  usage_time_limit_seconds?: number;
  usage_time_used_seconds: number;
  remaining_usage_time_seconds?: number;
  max_devices: number;
  simultaneous_sessions: number;
  created_at: string;
}

export interface PlanSnapshot {
  plan_id?: string;
  plan_name?: string;
  plan_code?: string;
  duration_value?: number;
  duration_unit?: string;
  validity_mode?: string;
  download_speed_kbps?: number;
  upload_speed_kbps?: number;
  data_limit_bytes?: number;
  max_devices?: number;
  simultaneous_sessions?: number;
  price?: string | number;
  currency?: string;
  snapshot_created_at?: string;
  [key: string]: unknown;
}

export interface AccessEntitlementDetail extends AccessEntitlement {
  idle_timeout_seconds?: number;
  session_timeout_seconds?: number;
  plan_snapshot: PlanSnapshot;
  suspended_at?: string;
  suspended_by_email?: string;
  suspension_reason?: string;
  revoked_at?: string;
  revoked_by_email?: string;
  revocation_reason?: string;
  created_by_email?: string;
  is_authorizable: boolean;
  authorization_status: string;
  updated_at: string;
}

export interface EntitlementSummaryMetrics {
  total_entitlements: number;
  active: number;
  expiring_soon: number;
  suspended: number;
  expired: number;
  revoked: number;
  pending: number;
}

export interface ManualGrantPayload {
  company_id: string;
  plan_id: string;
  customer_id?: string;
  reason: string;
  activate_immediately?: boolean;
}

export type SessionStatus = 'ACTIVE' | 'STOPPED' | 'STALE';
export type DisconnectStatus = 'PENDING' | 'SENDING' | 'ACKNOWLEDGED' | 'FAILED' | 'TIMEOUT' | 'CANCELLED';
export type SessionDisconnectTrigger = 'MANUAL' | 'ENTITLEMENT_SUSPENDED' | 'ENTITLEMENT_REVOKED' | 'DATA_QUOTA_EXHAUSTED' | 'USAGE_TIME_EXHAUSTED' | 'ADMIN_SECURITY_ACTION';

export interface SessionDisconnectRequest {
  id: string;
  hotspot_session_id: string;
  trigger_type: SessionDisconnectTrigger;
  status: DisconnectStatus;
  reason: string;
  requested_by_email: string;
  nas_ip: string;
  requested_at: string;
  sent_at?: string;
  acknowledged_at?: string;
  failed_at?: string;
  attempt_count: number;
  response_code?: string;
  response_message?: string;
  last_error?: string;
  created_at: string;
}

export interface HotspotSession {
  id: string;
  acct_session_id: string;
  username: string;
  mac_address: string;
  ip_address?: string;
  device_name?: string;
  status: SessionStatus;
  entitlement_id: string;
  entitlement_reference: string;
  plan_name: string;
  radius_client_name: string;
  started_at: string;
  last_accounting_at?: string;
  ended_at?: string;
  input_bytes: number;
  output_bytes: number;
  total_bytes: number;
  session_seconds: number;
  termination_reason?: string;
  latest_disconnect_status?: string;
  created_at: string;
}

export interface SessionSummaryMetrics {
  total_sessions: number;
  active: number;
  stopped: number;
  stale: number;
}

export interface PublicHotspotConfig {
  id: string;
  name: string;
  slug: string;
  ssid: string;
  company_name: string;
  brand_name: string;
  headline: string;
  welcome_text: string;
  primary_color: string;
  logo_url?: string;
  support_phone?: string;
  terms_url?: string;
  privacy_url?: string;
  default_language: 'EN' | 'SW';
  gateway_ip?: string;
  login_url?: string;
  router_login_url: string;
  context_token?: string;
  is_active: boolean;
}

export interface PublicPortalContextResponse {
  hotspot: PublicHotspotConfig;
  login_url: string;
  gateway_ip: string;
  context_token: string;
  session_context: {
    mac?: string;
    ip?: string;
    link_orig?: string;
    gateway_ip?: string;
  };
  plans: PublicPlan[];
}

export type PortalHandoffStatus = 'IDLE' | 'ACTIVATING' | 'CONNECTED' | 'FAILED';

export interface PublicVoucherSubmitPayload {
  voucher_code: string;
  customer_phone?: string;
  language?: 'EN' | 'SW';
  context_token?: string;
  link_login?: string;
}

export interface PublicVoucherRedeemResponse {
  success: boolean;
  username?: string;
  password?: string;
  entitlement_reference?: string;
  plan_name?: string;
  download_speed_kbps?: number;
  upload_speed_kbps?: number;
  remaining_seconds?: number;
  remaining_data_bytes?: number;
  router_login_url?: string;
  gateway_ip?: string;
  error_code?: string;
  message?: string;
}

export interface CustomerSessionStatus {
  connected: boolean;
  status: string;
  username: string;
  mac_address?: string;
  plan_name?: string;
  session_seconds?: number;
  total_bytes?: number;
  input_bytes?: number;
  output_bytes?: number;
  started_at?: string;
  remaining_seconds?: number;
  remaining_data_bytes?: number;
}

export interface PublicPlan {
  id: string;
  name: string;
  description: string;
  price: string;
  currency: string;
  validity_mode: 'CONTINUOUS' | 'USAGE_TIME' | 'CALENDAR';
  duration_value: number;
  duration_unit: 'HOURS' | 'DAYS' | 'WEEKS' | 'MONTHS';
  download_speed_kbps?: number;
  upload_speed_kbps?: number;
  data_limit_bytes?: number;
  max_devices: number;
  simultaneous_sessions: number;
}

export interface PublicPurchaseStatusResponse {
  reference: string;
  status: 'CREATED' | 'PAYMENT_PENDING' | 'PAID' | 'ENTITLEMENT_CREATED' | 'FULFILLED' | 'FAILED' | 'EXPIRED';
  amount: string;
  currency: string;
  customer_phone: string;
  plan_name: string;
  voucher_code?: string;
  checkout_url?: string;
  router_login_url?: string;
  gateway_ip?: string;
  error_message?: string;
  created_at: string;
  completed_at?: string;
}

export interface PaymentTransaction {
  id: string;
  purchase: string;
  purchase_reference: string;
  plan_name: string;
  provider: 'SNIPPE' | 'MANUAL';
  provider_reference: string;
  internal_reference: string;
  amount: string;
  currency: string;
  status: 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED' | 'EXPIRED' | 'CANCELLED';
  payment_method: string;
  customer_phone: string;
  checkout_url?: string;
  created_at: string;
  completed_at?: string;
  failed_at?: string;
  updated_at: string;
}

export interface AccessPurchase {
  id: string;
  reference: string;
  hotspot?: string;
  hotspot_name?: string;
  plan: string;
  plan_name: string;
  customer_phone: string;
  amount: string;
  currency: string;
  status: 'CREATED' | 'PAYMENT_PENDING' | 'PAID' | 'ENTITLEMENT_CREATED' | 'FULFILLED' | 'FAILED' | 'EXPIRED';
  voucher_code?: string;
  entitlement_reference?: string;
  client_mac?: string;
  ip_address?: string;
  error_message?: string;
  created_at: string;
  completed_at?: string;
}

export interface PaymentSettings {
  id: string;
  provider: string;
  is_enabled: boolean;
  environment: 'sandbox' | 'live';
  api_base_url: string;
  default_currency: string;
  api_key_masked: string;
  webhook_secret_masked: string;
  created_at: string;
  updated_at: string;
}

export interface HotspotWalledGardenEntry {
  id: string;
  hotspot?: string;
  entry_type: 'DOMAIN' | 'IP' | 'CIDR';
  host?: string;
  address?: string;
  protocol?: string;
  port?: string;
  purpose: 'PORTAL' | 'PAYMENT' | 'SYSTEM' | 'CUSTOM';
  description: string;
  is_active: boolean;
  created_at: string;
}

export interface AntiTetheringPolicy {
  id: string;
  hotspot_id: string;
  hotspot_name: string;
  enabled: boolean;
  max_devices: number;
  simultaneous_sessions: number;
  ttl_lock_enabled: boolean;
  ttl_lock_value: number;
  detect_ttl_63: boolean;
  detect_ttl_127: boolean;
  strict_mode: boolean;
  ipv6_policy: 'DISABLED' | 'BLOCK_IPV6' | 'FUTURE_MANAGED';
  last_synced_at?: string;
  last_router_status?: Record<string, any>;
  created_at: string;
  updated_at: string;
}

export interface AntiTetheringRouterStatus {
  status: 'ACTIVE' | 'PARTIALLY_ACTIVE' | 'DISABLED' | 'OUT_OF_SYNC' | 'ROUTER_UNREACHABLE' | 'ERROR';
  router_reachable: boolean;
  ttl_lock_active: boolean;
  ttl_63_active: boolean;
  ttl_127_active: boolean;
  rules_found: number;
  last_synced_at?: string;
  error?: string;
  details?: {
    ttl_lock?: { id: string; new_ttl?: string; packets: number; bytes: number };
    ttl_63?: { id: string; packets: number; bytes: number };
    ttl_127?: { id: string; packets: number; bytes: number };
  };
}

export interface AntiTetheringCounters {
  ttl_lock: { packets: number; bytes: number; active: boolean };
  ttl_63: { packets: number; bytes: number; active: boolean };
  ttl_127: { packets: number; bytes: number; active: boolean };
  total_blocked_packets: number;
  total_blocked_bytes: number;
  router_reachable: boolean;
}

export type CustomerStatus = 'ACTIVE' | 'SUSPENDED' | 'BLOCKED' | 'ARCHIVED';

export interface CustomerDevice {
  id: string;
  mac_address: string;
  device_name?: string;
  device_type: 'MOBILE' | 'LAPTOP' | 'TABLET' | 'OTHER';
  is_trusted: boolean;
  is_blocked: boolean;
  first_seen_at: string;
  last_seen_at?: string;
  created_at: string;
}

export interface CustomerActiveSubscriptionInfo {
  id: string;
  plan_name: string;
  status: SubscriptionStatus;
  current_period_end?: string;
  remaining_seconds: number;
}

export interface Customer {
  id: string;
  company_id: string;
  phone: string;
  normalized_phone: string;
  first_name: string;
  last_name: string;
  full_name: string;
  email?: string;
  status: CustomerStatus;
  language: 'EN' | 'SW';
  notes?: string;
  devices_count: number;
  active_subscription?: CustomerActiveSubscriptionInfo;
  total_spent: string;
  last_seen_at?: string;
  created_at: string;
  updated_at: string;
}

export type SubscriptionStatus = 'PENDING' | 'ACTIVE' | 'GRACE' | 'SUSPENDED' | 'EXPIRED' | 'CANCELLED';
export type SubscriptionRenewalMode = 'MANUAL' | 'AUTO_RENEW_FUTURE';
export type SubscriptionSource = 'SELF_SERVICE_PAYMENT' | 'ADMIN_CREATED' | 'VOUCHER_UPGRADE' | 'PROMOTIONAL' | 'MANUAL';

export interface SubscriptionEvent {
  id: string;
  event_type: string;
  old_status: string;
  new_status: string;
  actor_email?: string;
  source: string;
  metadata: Record<string, any>;
  created_at: string;
}

export interface Subscription {
  id: string;
  company_id: string;
  customer_id: string;
  customer_phone: string;
  customer_name: string;
  plan_id: string;
  plan_name: string;
  plan_price: string;
  plan_currency: string;
  hotspot_id?: string;
  hotspot_name?: string;
  status: SubscriptionStatus;
  started_at?: string;
  current_period_start?: string;
  current_period_end?: string;
  grace_period_end?: string;
  remaining_seconds: number;
  is_valid_now: boolean;
  renewal_mode: SubscriptionRenewalMode;
  source: SubscriptionSource;
  plan_snapshot: Record<string, any>;
  events?: SubscriptionEvent[];
  created_at: string;
  updated_at: string;
}

export interface CustomerSubscriptionSettings {
  id?: string;
  grace_period_minutes: number;
  otp_expiry_minutes: number;
  otp_resend_cooldown_seconds: number;
  remind_1day_before: boolean;
  remind_1hour_before: boolean;
  remind_at_expiry: boolean;
  allow_self_service: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface CustomerTimelineItem {
  type: 'SUBSCRIPTION_EVENT' | 'PAYMENT' | 'HOTSPOT_SESSION' | 'SMS';
  title: string;
  description: string;
  timestamp: string;
  metadata: Record<string, any>;
}

// ==========================================
// INFRASTRUCTURE DOMAIN TYPES (PHASES A - E)
// ==========================================

export type SiteType =
  | 'BRANCH'
  | 'HOTEL'
  | 'RESTAURANT'
  | 'CAFE'
  | 'BUS_TERMINAL'
  | 'MALL'
  | 'OFFICE'
  | 'PUBLIC_SITE'
  | 'OTHER';

export type LocationStatus = 'ACTIVE' | 'INACTIVE' | 'MAINTENANCE';

export type LocationNetworkHealth = 'HEALTHY' | 'DEGRADED' | 'OFFLINE' | 'UNKNOWN';

export interface LocationNetworkSummary {
  network_health: LocationNetworkHealth;
  total_routers: number;
  online_routers: number;
  degraded_routers: number;
  unreachable_routers: number;
  total_hotspots: number;
  active_hotspots: number;
  active_sessions: number;
}

export interface LocationSummary {
  id: string;
  name: string;
  code: string;
  region: string;
  district: string;
  address: string;
  latitude?: string | null;
  longitude?: string | null;
  timezone: string;
  status: LocationStatus;
  site_type: SiteType;
  operating_hours?: string;
  installation_date?: string | null;
  external_reference?: string;
  contact_person?: string;
  contact_phone?: string;
  notes?: string;
  is_active: boolean;
  network_health: LocationNetworkHealth;
  router_count: number;
  online_router_count: number;
  degraded_router_count: number;
  unreachable_router_count: number;
  hotspot_count: number;
  active_hotspot_count: number;
  active_session_count: number;
  created_at: string;
  updated_at: string;
}

export interface LocationDetail extends LocationSummary {
  network_summary: LocationNetworkSummary;
  detail?: string;
}

export interface LocationRouterSummary {
  id: string;
  name: string;
  identity: string;
  vendor: string;
  model: string;
  management_ip: string;
  api_port: number;
  use_tls: boolean;
  has_credentials: boolean;
  health_status: RouterHealthStatus;
  health_message: string;
  last_health_check_at: string | null;
  last_seen_at: string | null;
  hotspots_count: number;
  created_at: string;
}

export interface LocationHotspotSummary {
  id: string;
  name: string;
  slug: string;
  ssid: string;
  is_default: boolean;
  interface_name: string;
  gateway_ip: string;
  subnet_mask: string;
  status: HotspotStatus;
  is_active: boolean;
  router_id: string | null;
  router_name: string | null;
  plans_count: number;
  active_sessions_count: number;
  anti_tethering_enabled?: boolean;
  created_at: string;
}

export interface LocationSessionSummary {
  id: string;
  session_id: string;
  username: string;
  client_mac: string;
  client_ip: string | null;
  device_name?: string;
  hotspot_id: string | null;
  hotspot_name: string | null;
  status: string;
  started_at: string;
  last_accounting_at: string | null;
  stop_time: string | null;
  bytes_in: number;
  bytes_out: number;
  total_bytes: number;
  duration_seconds: number;
  ip_address?: string;
  mac_address?: string;
  plan_name?: string;
  start_time?: string;
}

export type RouterHealthStatus = 'ONLINE' | 'HEALTHY' | 'DEGRADED' | 'UNREACHABLE' | 'UNKNOWN';

export interface RouterSummary {
  id: string;
  name: string;
  identity: string;
  vendor: string;
  model: string;
  serial_number: string;
  firmware_version?: string;
  routeros_version?: string;
  architecture?: string;
  management_ip: string;
  api_port: number;
  use_tls: boolean;
  uplink_interface?: string;
  uplink_interface_name?: string;
  has_credentials: boolean;
  api_username?: string;
  health_status: RouterHealthStatus;
  health_message: string;
  last_health_check_at: string | null;
  last_seen_at: string | null;
  location: {
    id: string;
    name: string;
    code?: string;
  } | null;
  location_id?: string;
  location_name?: string;
  hotspot_count?: number;
  hotspots_count?: number;
  cached_system_info?: Record<string, any>;
  system_resources?: Record<string, any>;
  fallback_management_ip?: string;
  created_at: string;
  updated_at: string;
}

export interface RouterDetail extends RouterSummary {
  company: string;
  radius_client: {
    id: string;
    nas_name: string;
    ip_address: string;
    nas_identifier: string;
    coa_port: number;
    is_active: boolean;
  } | null;
  hotspots: Array<{
    id: string;
    name: string;
    slug: string;
    ssid: string;
    is_default: boolean;
    status: string;
    interface?: string;
    interface_name?: string;
    gateway_ip: string;
    subnet_mask: string;
    is_active?: boolean;
  }>;
  uplink_profiles_count?: number;
}

export interface RouterTestConnectionResult {
  success: boolean;
  latency_ms: number | null;
  version?: string | null;
  routeros_version?: string | null;
  identity: string | null;
  board_name?: string | null;
  model?: string | null;
  architecture?: string | null;
  cpu_load?: number | null;
  uptime?: string | null;
  detail?: string | null;
  message?: string | null;
  authenticated?: boolean;
  error?: string | null;
  details?: Record<string, any>;
}

export interface RouterHealthResponse {
  health_status: RouterHealthStatus;
  health_message: string;
  last_health_check_at: string;
  last_seen_at: string | null;
  telemetry?: {
    cpu_load?: number;
    free_memory_mb?: number;
    total_memory_mb?: number;
    uptime?: string;
    board_name?: string;
    version?: string;
  };
}

export interface RouterProvisionStep {
  name: string;
  success: boolean;
  message: string;
  details?: Record<string, any>;
  timestamp: string;
}

export interface RouterProvisionResult {
  success: boolean;
  router_id: string;
  router_name: string;
  management_ip: string;
  health_status: string;
  elapsed_ms: number;
  steps: RouterProvisionStep[];
  telemetry?: Record<string, any>;
}

export interface RouterBootstrapScript {
  router_id: string;
  router_name: string;
  management_ip: string;
  command: string;
  download_url: string;
  script: string;
}

export type HotspotStatus = 'ACTIVE' | 'DISABLED';

export interface HotspotSummary {
  id: string;
  name: string;
  slug: string;
  ssid: string;
  is_default: boolean;
  status: HotspotStatus;
  is_active: boolean;
  location: {
    id: string;
    name: string;
    code: string;
  } | null;
  router: {
    id: string;
    name: string;
    management_ip: string;
  } | null;
  interface_name: string;
  interface?: string;
  gateway_ip: string;
  subnet_mask: string;
  plans_count: number;
  active_sessions_count: number;
  active_users_count?: number;
  anti_tethering_enabled: boolean;
  is_anti_tethering_enabled?: boolean;
  created_at: string;
  updated_at: string;
}

export interface HotspotDetail extends HotspotSummary {
  server_name: string;
  router_login_url: string;
  brand_name: string;
  headline: string;
  portal_title?: string;
  welcome_text: string;
  welcome_message?: string;
  primary_color: string;
  logo_url: string;
  support_phone: string;
  terms_url: string;
  privacy_url: string;
  default_language: 'EN' | 'SW';
  plans: Array<{
    id: string;
    name: string;
    code: string;
    price: string;
    currency: string;
    duration_value: number;
    duration_unit_display: string;
    is_active: boolean;
  }>;
}


