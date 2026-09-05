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
  router_login_url: string;
  is_active: boolean;
}

export interface PublicVoucherSubmitPayload {
  voucher_code: string;
  customer_phone?: string;
  language?: 'EN' | 'SW';
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



