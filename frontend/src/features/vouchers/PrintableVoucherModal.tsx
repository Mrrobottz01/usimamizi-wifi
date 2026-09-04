import React, { useEffect, useState } from 'react';
import { ApiError, PrintableVoucherCard } from '../../types';
import { apiClient } from '../../lib/api-client';

interface PrintableVoucherModalProps {
  isOpen: boolean;
  onClose: () => void;
  batchId: string;
  batchReference: string;
}

export const PrintableVoucherModal: React.FC<PrintableVoucherModalProps> = ({
  isOpen,
  onClose,
  batchId,
  batchReference,
}) => {
  const [cards, setCards] = useState<PrintableVoucherCard[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen && batchId) {
      setLoading(true);
      setError(null);
      apiClient
        .get<PrintableVoucherCard[]>(`/api/v1/voucher-batches/${batchId}/printable-cards/`)
        .then((res: { data: PrintableVoucherCard[] }) => {
          setCards(res.data);
        })
        .catch((err: unknown) => {
          const apiErr = err as ApiError;
          setError(apiErr?.detail || 'Failed to load printable voucher cards.');
        })
        .finally(() => {
          setLoading(false);
        });
    }
  }, [isOpen, batchId]);

  if (!isOpen) return null;

  const handlePrint = () => {
    window.print();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-sm p-4 overflow-y-auto">
      {/* Modal Container */}
      <div className="w-full max-w-5xl rounded-2xl border border-slate-200 bg-white shadow-2xl dark:border-slate-800 dark:bg-slate-900 my-8 flex flex-col max-h-[90vh]">
        {/* Header - Hidden in Print */}
        <div className="print:hidden flex items-center justify-between border-b border-slate-200 px-6 py-4 dark:border-slate-800">
          <div>
            <h2 className="text-xl font-bold text-slate-900 dark:text-slate-100">
              Printable Voucher Sheet ({batchReference})
            </h2>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              {cards.length} voucher card(s) formatted for standard A4 paper printing.
            </p>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={handlePrint}
              disabled={loading || cards.length === 0}
              className="flex items-center gap-2 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-700 transition shadow-sm disabled:opacity-50"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z" />
              </svg>
              Print Sheet (A4)
            </button>
            <button
              onClick={onClose}
              className="rounded-lg border border-slate-300 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
            >
              Close
            </button>
          </div>
        </div>

        {/* Content Body */}
        <div className="flex-1 overflow-y-auto p-6 bg-slate-50 dark:bg-slate-950/50 print:p-0 print:bg-white print:overflow-visible">
          {error && (
            <div className="mb-4 rounded-lg bg-rose-50 p-4 text-sm text-rose-600 dark:bg-rose-950/40 dark:text-rose-400 print:hidden">
              {error}
            </div>
          )}

          {loading ? (
            <div className="py-20 text-center text-slate-500 font-medium">
              Generating printable card sheets...
            </div>
          ) : (
            <div className="print-grid grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 print:grid-cols-2 print:gap-4">
              {cards.map((card) => (
                <div
                  key={card.id}
                  className="voucher-card relative rounded-xl border-2 border-dashed border-slate-300 bg-white p-5 shadow-sm print:shadow-none print:border-slate-400 print:page-break-inside-avoid dark:border-slate-700 dark:bg-slate-900"
                >
                  {/* Card Header: Brand / SSID */}
                  <div className="flex items-start justify-between border-b border-slate-100 pb-3 dark:border-slate-800">
                    <div>
                      <div className="text-[10px] font-bold uppercase tracking-wider text-emerald-600 dark:text-emerald-400">
                        Wi-Fi HotSpot Access
                      </div>
                      <div className="text-base font-extrabold text-slate-900 dark:text-slate-100">
                        {card.ssid}
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="text-base font-black text-slate-900 dark:text-slate-100">
                        {card.price} <span className="text-xs font-semibold">{card.currency}</span>
                      </div>
                      <div className="text-[10px] text-slate-500 font-medium">{card.plan_name}</div>
                    </div>
                  </div>

                  {/* Plan Features */}
                  <div className="my-3 flex flex-wrap items-center gap-2 text-[11px] text-slate-600 dark:text-slate-400">
                    <span className="rounded bg-slate-100 px-2 py-0.5 font-medium dark:bg-slate-800">
                      ⏱ {card.duration_display}
                    </span>
                    <span className="rounded bg-slate-100 px-2 py-0.5 font-medium dark:bg-slate-800">
                      🚀 {card.speed_display}
                    </span>
                    <span className="rounded bg-slate-100 px-2 py-0.5 font-medium dark:bg-slate-800">
                      📊 {card.quota_display}
                    </span>
                  </div>

                  {/* Voucher Code Box & QR */}
                  <div className="my-3 flex items-center justify-between gap-3 rounded-lg bg-emerald-50/70 p-3 border border-emerald-200 dark:bg-emerald-950/20 dark:border-emerald-900/50">
                    <div className="flex-1">
                      <div className="text-[10px] font-semibold text-emerald-800 dark:text-emerald-300 uppercase tracking-wider">
                        Voucher Code
                      </div>
                      <div className="text-lg font-black tracking-widest text-emerald-950 dark:text-emerald-200 font-mono select-all">
                        {card.code}
                      </div>
                      <div className="text-[9px] text-slate-500 dark:text-slate-400">
                        Device limit: {card.devices} device(s)
                      </div>
                    </div>
                    <div className="w-16 h-16 bg-white p-1 rounded border border-slate-200 flex-shrink-0 flex items-center justify-center">
                      <img
                        src={`https://api.qrserver.com/v1/create-qr-code/?size=100x100&margin=0&data=${encodeURIComponent(card.qr_url)}`}
                        alt="Scan QR"
                        className="w-14 h-14"
                        loading="lazy"
                      />
                    </div>
                  </div>

                  {/* Quick Instructions */}
                  <div className="border-t border-slate-100 pt-2 text-[10px] text-slate-500 dark:border-slate-800 dark:text-slate-400 space-y-0.5">
                    <p className="font-semibold text-slate-700 dark:text-slate-300">How to connect:</p>
                    <p>1. Connect device to Wi-Fi <span className="font-semibold text-slate-800 dark:text-slate-200">{card.ssid}</span></p>
                    <p>2. Scan QR or visit <span className="font-semibold font-mono text-emerald-700 dark:text-emerald-400">login.usimamizi.lab</span></p>
                    <p>3. Enter code above to activate high-speed Internet</p>
                  </div>

                  {/* Footer metadata */}
                  <div className="mt-2 flex items-center justify-between text-[8px] text-slate-400">
                    <span>Batch: {card.batch_ref}</span>
                    <span>Valid from first activation</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      <style>{`
        @media print {
          body * {
            visibility: hidden;
          }
          .voucher-card, .voucher-card * {
            visibility: visible;
          }
          .print-grid {
            visibility: visible;
            display: grid !important;
            grid-template-columns: repeat(2, minmax(0, 1fr)) !important;
            gap: 12px !important;
            padding: 10px !important;
          }
          .voucher-card {
            page-break-inside: avoid;
            break-inside: avoid;
            border: 1.5px dashed #475569 !important;
            background: #ffffff !important;
            color: #0f172a !important;
          }
          @page {
            size: A4 portrait;
            margin: 10mm;
          }
        }
      `}</style>
    </div>
  );
};
