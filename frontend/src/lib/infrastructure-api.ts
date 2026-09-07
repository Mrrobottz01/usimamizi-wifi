import { apiClient } from './api-client';
import {
  LocationSummary,
  LocationDetail,
  LocationRouterSummary,
  LocationHotspotSummary,
  LocationSessionSummary,
  RouterSummary,
  RouterDetail,
  RouterTestConnectionResult,
  RouterHealthResponse,
  RouterProvisionResult,
  RouterBootstrapScript,
  HotspotSummary,
  HotspotDetail,
} from '../types';

/**
 * ============================================================================
 * Locations Infrastructure API
 * /api/v1/locations/
 * ============================================================================
 */
export const locationsApi = {
  list: async (params?: {
    q?: string;
    site_type?: string;
    status?: string;
    is_active?: boolean;
    ordering?: string;
    company_id?: string;
  }): Promise<LocationSummary[]> => {
    const query = new URLSearchParams();
    if (params?.q) query.set('q', params.q);
    if (params?.site_type) query.set('site_type', params.site_type);
    if (params?.status) query.set('status', params.status);
    if (params?.is_active !== undefined) query.set('is_active', String(params.is_active));
    if (params?.ordering) query.set('ordering', params.ordering);
    if (params?.company_id) query.set('company_id', params.company_id);

    const queryString = query.toString() ? `?${query.toString()}` : '';
    const res = await apiClient.get<LocationSummary[]>(`/locations/${queryString}`);
    return res.data;
  },

  get: async (id: string, company_id?: string): Promise<LocationDetail> => {
    const queryString = company_id ? `?company_id=${company_id}` : '';
    const res = await apiClient.get<LocationDetail>(`/locations/${id}/${queryString}`);
    return res.data;
  },

  create: async (data: Partial<LocationSummary> & { company_id?: string }): Promise<LocationDetail> => {
    const res = await apiClient.post<LocationDetail>('/locations/', data);
    return res.data;
  },

  update: async (id: string, data: Partial<LocationSummary> & { company_id?: string }): Promise<LocationDetail> => {
    const res = await apiClient.patch<LocationDetail>(`/locations/${id}/`, data);
    return res.data;
  },

  delete: async (id: string, company_id?: string): Promise<{ action: string; detail: string }> => {
    const queryString = company_id ? `?company_id=${company_id}` : '';
    const res = await apiClient.delete<{ action: string; detail: string }>(`/locations/${id}/${queryString}`);
    return res.data;
  },

  reactivate: async (id: string, company_id?: string): Promise<LocationDetail> => {
    const queryString = company_id ? `?company_id=${company_id}` : '';
    const res = await apiClient.post<LocationDetail>(`/locations/${id}/reactivate/${queryString}`);
    return res.data;
  },

  getRouters: async (id: string, company_id?: string): Promise<LocationRouterSummary[]> => {
    const queryString = company_id ? `?company_id=${company_id}` : '';
    const res = await apiClient.get<LocationRouterSummary[]>(`/locations/${id}/routers/${queryString}`);
    return res.data;
  },

  getHotspots: async (id: string, company_id?: string): Promise<LocationHotspotSummary[]> => {
    const queryString = company_id ? `?company_id=${company_id}` : '';
    const res = await apiClient.get<LocationHotspotSummary[]>(`/locations/${id}/hotspots/${queryString}`);
    return res.data;
  },

  getSessions: async (id: string, company_id?: string): Promise<LocationSessionSummary[]> => {
    const queryString = company_id ? `?company_id=${company_id}` : '';
    const res = await apiClient.get<LocationSessionSummary[]>(`/locations/${id}/sessions/${queryString}`);
    return res.data;
  },

  moveRouter: async (
    id: string,
    router_id: string,
    company_id?: string
  ): Promise<{ success: boolean; router_id: string; target_location_id: string; updated_hotspots_count: number }> => {
    const queryString = company_id ? `?company_id=${company_id}` : '';
    const res = await apiClient.post<{
      success: boolean;
      router_id: string;
      target_location_id: string;
      updated_hotspots_count: number;
    }>(`/locations/${id}/move-router/${queryString}`, { router_id });
    return res.data;
  },
};

/**
 * ============================================================================
 * Routers Fleet API
 * /api/v1/routers/
 * ============================================================================
 */
export const routersApi = {
  list: async (params?: {
    q?: string;
    location_id?: string;
    health_status?: string;
    ordering?: string;
    company_id?: string;
  }): Promise<RouterSummary[]> => {
    const query = new URLSearchParams();
    if (params?.q) query.set('q', params.q);
    if (params?.location_id) query.set('location_id', params.location_id);
    if (params?.health_status) query.set('health_status', params.health_status);
    if (params?.ordering) query.set('ordering', params.ordering);
    if (params?.company_id) query.set('company_id', params.company_id);

    const queryString = query.toString() ? `?${query.toString()}` : '';
    const res = await apiClient.get<RouterSummary[]>(`/routers/${queryString}`);
    return res.data;
  },

  get: async (id: string, company_id?: string): Promise<RouterDetail> => {
    const queryString = company_id ? `?company_id=${company_id}` : '';
    const res = await apiClient.get<RouterDetail>(`/routers/${id}/${queryString}`);
    return res.data;
  },

  create: async (data: Record<string, any>): Promise<RouterDetail> => {
    const res = await apiClient.post<RouterDetail>('/routers/', data);
    return res.data;
  },

  update: async (id: string, data: Record<string, any>): Promise<RouterDetail> => {
    const res = await apiClient.patch<RouterDetail>(`/routers/${id}/`, data);
    return res.data;
  },

  delete: async (id: string, company_id?: string): Promise<{ success: boolean; message: string }> => {
    const queryString = company_id ? `?company_id=${company_id}` : '';
    const res = await apiClient.delete<{ success: boolean; message: string }>(`/routers/${id}/${queryString}`);
    return res.data;
  },

  updateCredentials: async (
    id: string,
    data: {
      api_username?: string;
      api_password?: string;
      api_port?: number;
      use_tls?: boolean;
    }
  ): Promise<RouterDetail> => {
    const res = await apiClient.post<RouterDetail>(`/routers/${id}/credentials/`, data);
    return res.data;
  },

  testConnection: async (id: string, company_id?: string): Promise<RouterTestConnectionResult> => {
    const queryString = company_id ? `?company_id=${company_id}` : '';
    const res = await apiClient.post<RouterTestConnectionResult>(`/routers/${id}/test-connection/${queryString}`);
    return res.data;
  },

  refreshHealth: async (id: string, company_id?: string): Promise<RouterHealthResponse> => {
    const queryString = company_id ? `?company_id=${company_id}` : '';
    const res = await apiClient.post<RouterHealthResponse>(`/routers/${id}/refresh-health/${queryString}`);
    return res.data;
  },

  provision: async (
    id: string,
    options?: {
      radius_ip?: string;
      shared_secret?: string;
      enable_anti_tethering?: boolean;
      enable_radius?: boolean;
      enable_hotspot?: boolean;
      enable_walled_garden?: boolean;
    }
  ): Promise<{ result: RouterProvisionResult; router: RouterDetail }> => {
    const res = await apiClient.post<{ result: RouterProvisionResult; router: RouterDetail }>(
      `/routers/${id}/provision/`,
      options || {}
    );
    return res.data;
  },

  getBootstrapScript: async (
    id: string,
    params?: {
      radius_ip?: string;
      shared_secret?: string;
      anti_tethering?: boolean;
      radius?: boolean;
      hotspot?: boolean;
      walled_garden?: boolean;
    }
  ): Promise<RouterBootstrapScript> => {
    const query = new URLSearchParams();
    if (params?.radius_ip) query.set('radius_ip', params.radius_ip);
    if (params?.shared_secret) query.set('shared_secret', params.shared_secret);
    if (params?.anti_tethering !== undefined) query.set('anti_tethering', String(params.anti_tethering));
    if (params?.radius !== undefined) query.set('radius', String(params.radius));
    if (params?.hotspot !== undefined) query.set('hotspot', String(params.hotspot));
    if (params?.walled_garden !== undefined) query.set('walled_garden', String(params.walled_garden));

    const queryString = query.toString() ? `?${query.toString()}` : '';
    const res = await apiClient.get<RouterBootstrapScript>(`/routers/${id}/bootstrap-script/${queryString}`);
    return res.data;
  },
};

/**
 * ============================================================================
 * Hotspots Fleet API
 * /api/v1/hotspots/
 * ============================================================================
 */
export const hotspotsApi = {
  list: async (params?: {
    q?: string;
    location_id?: string;
    router_id?: string;
    is_active?: boolean;
    ordering?: string;
    company_id?: string;
  }): Promise<HotspotSummary[]> => {
    const query = new URLSearchParams();
    if (params?.q) query.set('q', params.q);
    if (params?.location_id) query.set('location_id', params.location_id);
    if (params?.router_id) query.set('router_id', params.router_id);
    if (params?.is_active !== undefined) query.set('is_active', String(params.is_active));
    if (params?.ordering) query.set('ordering', params.ordering);
    if (params?.company_id) query.set('company_id', params.company_id);

    const queryString = query.toString() ? `?${query.toString()}` : '';
    const res = await apiClient.get<HotspotSummary[]>(`/hotspots/${queryString}`);
    return res.data;
  },

  get: async (id: string, company_id?: string): Promise<HotspotDetail> => {
    const queryString = company_id ? `?company_id=${company_id}` : '';
    const res = await apiClient.get<HotspotDetail>(`/hotspots/${id}/${queryString}`);
    return res.data;
  },

  create: async (data: Record<string, any>): Promise<HotspotDetail> => {
    const res = await apiClient.post<HotspotDetail>('/hotspots/', data);
    return res.data;
  },

  update: async (id: string, data: Record<string, any>): Promise<HotspotDetail> => {
    const res = await apiClient.patch<HotspotDetail>(`/hotspots/${id}/`, data);
    return res.data;
  },

  delete: async (id: string, company_id?: string): Promise<{ success: boolean; message: string }> => {
    const queryString = company_id ? `?company_id=${company_id}` : '';
    const res = await apiClient.delete<{ success: boolean; message: string }>(`/hotspots/${id}/${queryString}`);
    return res.data;
  },

  setDefault: async (id: string, company_id?: string): Promise<{ success: boolean; id: string; is_default: boolean }> => {
    const queryString = company_id ? `?company_id=${company_id}` : '';
    const res = await apiClient.post<{ success: boolean; id: string; is_default: boolean }>(
      `/hotspots/${id}/set-default/${queryString}`
    );
    return res.data;
  },

  getPlans: async (
    id: string,
    company_id?: string
  ): Promise<{
    hotspot_id: string;
    assigned_plan_ids: string[];
    plans: Array<{
      id: string;
      name: string;
      price: string;
      currency: string;
      duration_minutes?: number;
      data_limit_mb?: number;
      is_active: boolean;
    }>;
  }> => {
    const queryString = company_id ? `?company_id=${company_id}` : '';
    const res = await apiClient.get<{
      hotspot_id: string;
      assigned_plan_ids: string[];
      plans: Array<{
        id: string;
        name: string;
        price: string;
        currency: string;
        duration_minutes?: number;
        data_limit_mb?: number;
        is_active: boolean;
      }>;
    }>(`/hotspots/${id}/plans/${queryString}`);
    return res.data;
  },

  updatePlans: async (
    id: string,
    plan_ids: string[],
    company_id?: string
  ): Promise<{ success: boolean; assigned_plans_count: number; assigned_plan_ids: string[] }> => {
    const queryString = company_id ? `?company_id=${company_id}` : '';
    const res = await apiClient.post<{
      success: boolean;
      assigned_plans_count: number;
      assigned_plan_ids: string[];
    }>(`/hotspots/${id}/plans/${queryString}`, { plan_ids });
    return res.data;
  },
};
