import React, { useCallback, useEffect, useState } from 'react';
import { ApiError, Plan } from '../../types';
import { apiClient } from '../../lib/api-client';
import { useAuth } from '../../hooks/useAuth';
import { PlanFormModal } from './PlanFormModal';

export const PlansListPage: React.FC = () => {
  const { selectedCompany } = useAuth();
  const [plans, setPlans] = useState<Plan[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedPlan, setSelectedPlan] = useState<Plan | null>(null);

  const fetchPlans = useCallback(async () => {
    if (!selectedCompany) return;
    setLoading(true);
    setError(null);
    try {
      const res = await apiClient.get<Plan[]>(`/api/v1/plans/?company_id=${selectedCompany.id}&include_inactive=true`);
      setPlans(res.data);
    } catch (err: unknown) {
      const apiErr = err as ApiError;
      setError(apiErr?.detail || 'Failed to load plans.');
    } finally {
      setLoading(false);
    }
  }, [selectedCompany]);

  useEffect(() => {
    fetchPlans();
  }, [fetchPlans]);

  const handleDeactivate = async (plan: Plan) => {
    if (!confirm(`Are you sure you want to deactivate ${plan.name}?`)) return;
    try {
      await apiClient.delete(`/api/v1/plans/${plan.id}/`);
      fetchPlans();
    } catch (err: unknown) {
      const apiErr = err as ApiError;
      alert(apiErr?.detail || 'Failed to deactivate plan.');
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">Internet Access Plans</h1>
          <p className="text-sm text-slate-500 dark:text-slate-400">
            Define pricing, bandwidth speed limits, and validity parameters for your hotspot network.
          </p>
        </div>
        <button
          onClick={() => {
            setSelectedPlan(null);
            setIsModalOpen(true);
          }}
          className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700 transition"
        >
          + Create New Plan
        </button>
      </div>

      {error && (
        <div className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-600 dark:border-rose-900/50 dark:bg-rose-950/40 dark:text-rose-400">
          {error}
        </div>
      )}

      {loading ? (
        <div className="text-center py-12 text-slate-500">Loading plans...</div>
      ) : plans.length === 0 ? (
        <div className="rounded-xl border border-dashed border-slate-300 p-12 text-center dark:border-slate-800">
          <p className="text-slate-500 dark:text-slate-400 mb-4">No internet access plans configured yet.</p>
          <button
            onClick={() => setIsModalOpen(true)}
            className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700"
          >
            Create Your First Plan
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {plans.map((plan) => (
            <div
              key={plan.id}
              className={`rounded-xl border bg-white p-6 shadow-sm dark:bg-slate-900 transition ${
                plan.is_active ? 'border-slate-200 dark:border-slate-800' : 'border-slate-200 dark:border-slate-800 opacity-60'
              }`}
            >
              <div className="flex items-start justify-between mb-4">
                <div>
                  <span className="inline-block rounded bg-emerald-50 px-2 py-0.5 text-xs font-semibold text-emerald-700 dark:bg-emerald-950/50 dark:text-emerald-400 mb-1">
                    {plan.code}
                  </span>
                  <h3 className="text-lg font-bold text-slate-900 dark:text-slate-100">{plan.name}</h3>
                </div>
                <span
                  className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${
                    plan.is_active
                      ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-400'
                      : 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400'
                  }`}
                >
                  {plan.is_active ? 'Active' : 'Inactive'}
                </span>
              </div>

              <div className="text-2xl font-extrabold text-slate-900 dark:text-slate-100 mb-4">
                {plan.price} <span className="text-sm font-normal text-slate-500">{plan.currency}</span>
              </div>

              <div className="space-y-2 text-xs text-slate-600 dark:text-slate-400 mb-6">
                <div className="flex justify-between py-1 border-b border-slate-100 dark:border-slate-800">
                  <span>Duration</span>
                  <span className="font-semibold text-slate-900 dark:text-slate-200">
                    {plan.duration_value} {plan.duration_unit_display}
                  </span>
                </div>
                <div className="flex justify-between py-1 border-b border-slate-100 dark:border-slate-800">
                  <span>Validity Mode</span>
                  <span className="font-semibold text-slate-900 dark:text-slate-200">{plan.validity_mode_display}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-slate-100 dark:border-slate-800">
                  <span>Download / Upload</span>
                  <span className="font-semibold text-slate-900 dark:text-slate-200">
                    {plan.download_speed_kbps ? `${plan.download_speed_kbps / 1000} Mbps` : 'Unlimited'} /{' '}
                    {plan.upload_speed_kbps ? `${plan.upload_speed_kbps / 1000} Mbps` : 'Unlimited'}
                  </span>
                </div>
              </div>

              <div className="flex gap-2">
                <button
                  onClick={() => {
                    setSelectedPlan(plan);
                    setIsModalOpen(true);
                  }}
                  className="flex-1 rounded-lg border border-slate-300 py-2 text-xs font-medium text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
                >
                  Edit
                </button>
                {plan.is_active && (
                  <button
                    onClick={() => handleDeactivate(plan)}
                    className="rounded-lg border border-rose-200 px-3 py-2 text-xs font-medium text-rose-600 hover:bg-rose-50 dark:border-rose-900/50 dark:text-rose-400 dark:hover:bg-rose-950/40"
                  >
                    Deactivate
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      <PlanFormModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onSuccess={fetchPlans}
        initialData={selectedPlan}
      />
    </div>
  );
};
