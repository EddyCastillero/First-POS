<script>
  import { onMount } from 'svelte';
  import { showToast } from '../lib/stores.js';
  import { PosAPI } from '../lib/api.js';

  let selectedDate = getTodayString();
  let reportData = null;

  function getTodayString() {
    const now = new Date();
    const year = now.getFullYear();
    const month = String(now.getMonth() + 1).padStart(2, '0');
    const day = String(now.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
  }

  function setToday() {
    selectedDate = getTodayString();
    loadReport();
  }

  onMount(async () => {
    await loadReport();
  });

  async function loadReport() {
    try {
      reportData = await PosAPI.getDailyReport(selectedDate);
    } catch (err) {
      showToast(err.message, true);
    }
  }

  function formatTime(isoString) {
    if (!isoString) return '';
    const dateObj = new Date(isoString);
    return dateObj.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  }
</script>

<div>
  <!-- CABECERA Y FILTRO -->
  <div class="bg-white p-5 rounded-2xl shadow-sm border border-slate-200 mb-6 flex flex-wrap items-center justify-between gap-4">
    <div>
      <h2 class="text-xl font-bold text-slate-900 flex items-center gap-2">
        <span>📊</span> Reporte de Ventas por Día
      </h2>
      <p class="text-xs text-slate-500 mt-0.5">Auditoría diaria de ingresos, tickets cobrados, desglose por método de pago y ticket promedio.</p>
    </div>
    <div class="flex items-center space-x-3">
      <label for="report-date-input" class="text-xs font-semibold text-slate-600">Fecha a consultar:</label>
      <input
        type="date"
        id="report-date-input"
        bind:value={selectedDate}
        onchange={loadReport}
        class="px-3 py-2 bg-slate-50 border border-slate-300 rounded-xl text-xs font-bold text-slate-800 focus:ring-2 focus:ring-black"
      />
      <button onclick={setToday} class="px-3 py-2 bg-neutral-100 hover:bg-neutral-200 text-slate-700 text-xs font-semibold rounded-xl transition">
        Hoy
      </button>
    </div>
  </div>

  <!-- TARJETAS KPI -->
  {#if reportData}
    <div class="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
      <div class="bg-white p-4 rounded-2xl border border-slate-200 shadow-xs">
        <div class="flex items-center justify-between text-slate-500 text-xs font-medium mb-1">
          <span>Venta Total</span>
          <span>💰</span>
        </div>
        <div class="text-2xl font-black text-slate-900">${parseFloat(reportData.total_sales).toFixed(2)}</div>
        <div class="text-[10px] text-slate-400 mt-1">Ingresos brutos del día</div>
      </div>

      <div class="bg-white p-4 rounded-2xl border border-slate-200 shadow-xs">
        <div class="flex items-center justify-between text-slate-500 text-xs font-medium mb-1">
          <span>Ventas Efectivo</span>
          <span>💵</span>
        </div>
        <div class="text-2xl font-black text-emerald-700">${parseFloat(reportData.cash_sales).toFixed(2)}</div>
        <div class="text-[10px] text-slate-400 mt-1">Caja registradora</div>
      </div>

      <div class="bg-white p-4 rounded-2xl border border-slate-200 shadow-xs">
        <div class="flex items-center justify-between text-slate-500 text-xs font-medium mb-1">
          <span>Ventas Tarjeta</span>
          <span>💳</span>
        </div>
        <div class="text-2xl font-black text-blue-700">${parseFloat(reportData.card_sales).toFixed(2)}</div>
        <div class="text-[10px] text-slate-400 mt-1">Terminal bancaria</div>
      </div>

      <div class="bg-white p-4 rounded-2xl border border-slate-200 shadow-xs">
        <div class="flex items-center justify-between text-slate-500 text-xs font-medium mb-1">
          <span>Tickets Cobrados</span>
          <span>🧾</span>
        </div>
        <div class="text-2xl font-black text-slate-900">{reportData.orders_count}</div>
        <div class="text-[10px] text-slate-400 mt-1">Órdenes completadas</div>
      </div>

      <div class="bg-white p-4 rounded-2xl border border-slate-200 shadow-xs col-span-2 md:col-span-1">
        <div class="flex items-center justify-between text-slate-500 text-xs font-medium mb-1">
          <span>Ticket Promedio</span>
          <span>🎯</span>
        </div>
        <div class="text-2xl font-black text-purple-700">${parseFloat(reportData.average_ticket).toFixed(2)}</div>
        <div class="text-[10px] text-slate-400 mt-1">Consumo por comensal</div>
      </div>
    </div>

    <!-- TABLA DETALLE DE ÓRDENES -->
    <div class="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
      <div class="p-4 bg-slate-50 border-b border-slate-200 flex items-center justify-between">
        <h3 class="font-bold text-sm text-slate-800 flex items-center gap-2">
          <span>📋</span> Desglose de Órdenes del Día
        </h3>
        <span class="text-xs bg-slate-200 text-slate-700 px-2.5 py-1 rounded-full font-medium">
          {reportData.orders_count} {reportData.orders_count === 1 ? 'orden' : 'órdenes'}
        </span>
      </div>

      <div class="overflow-x-auto">
        <table class="w-full text-left text-xs text-slate-600">
          <thead class="bg-slate-50/70 text-slate-500 uppercase text-[10px] tracking-wider border-b border-slate-100">
            <tr>
              <th class="px-6 py-3.5">Folio</th>
              <th class="px-6 py-3.5">Hora</th>
              <th class="px-6 py-3.5">Cajero</th>
              <th class="px-6 py-3.5">Método de Pago</th>
              <th class="px-6 py-3.5">Artículos</th>
              <th class="px-6 py-3.5">Notas / Mesa</th>
              <th class="px-6 py-3.5 text-right font-bold">Total Cobrado</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100">
            {#if reportData.orders.length === 0}
              <tr>
                <td colspan="7" class="px-6 py-8 text-center text-slate-400 italic">
                  No hay órdenes registradas para la fecha seleccionada ({selectedDate}).
                </td>
              </tr>
            {:else}
              {#each reportData.orders as ord}
                <tr class="hover:bg-slate-50 transition">
                  <td class="px-6 py-4 font-mono font-bold text-slate-900">{ord.order_number}</td>
                  <td class="px-6 py-4 text-slate-500">{formatTime(ord.created_at)}</td>
                  <td class="px-6 py-4 font-medium text-slate-700">{ord.cashier_name}</td>
                  <td class="px-6 py-4">
                    {#if ord.payment_method === 'CASH'}
                      <span class="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">💵 Efectivo</span>
                    {:else}
                      <span class="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-blue-50 text-blue-700 border border-blue-200">💳 Tarjeta</span>
                    {/if}
                  </td>
                  <td class="px-6 py-4 text-slate-600 font-semibold">{ord.items_count} {ord.items_count === 1 ? 'artículo' : 'artículos'}</td>
                  <td class="px-6 py-4 text-slate-400 italic">{ord.notes || '—'}</td>
                  <td class="px-6 py-4 text-right font-black text-slate-900 text-sm">${parseFloat(ord.total_amount).toFixed(2)}</td>
                </tr>
              {/each}
            {/if}
          </tbody>
        </table>
      </div>
    </div>
  {/if}
</div>
