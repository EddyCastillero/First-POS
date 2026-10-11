<script>
  import { onMount } from 'svelte';
  import { ingredients, showToast } from '../lib/stores.js';
  import { InventoryAPI } from '../lib/api.js';

  // Merma en proceso
  let procIngId = '';
  let procGross = '';
  let procNet = '';
  let procReason = '';
  let procCook = '';

  // Merma general
  let genIngId = '';
  let genType = 'vida_util';
  let genQty = '';
  let genReason = '';

  $: calcWasteQty = (parseFloat(procGross) > 0 && parseFloat(procNet) >= 0 && parseFloat(procGross) >= parseFloat(procNet))
    ? (parseFloat(procGross) - parseFloat(procNet)).toFixed(3)
    : '0.000';

  $: calcWastePct = (parseFloat(procGross) > 0 && parseFloat(procNet) >= 0 && parseFloat(procGross) >= parseFloat(procNet))
    ? (((parseFloat(procGross) - parseFloat(procNet)) / parseFloat(procGross)) * 100).toFixed(2) + '%'
    : '0.00%';

  onMount(async () => {
    try {
      const data = await InventoryAPI.getIngredients();
      ingredients.set(data);
    } catch (err) {
      console.error(err);
    }
  });

  async function handleProcessWaste(e) {
    e.preventDefault();
    try {
      const res = await InventoryAPI.registerProcessWaste({
        ingredient_id: procIngId,
        gross_quantity: parseFloat(procGross),
        net_quantity: parseFloat(procNet),
        reason: procReason.trim() || null,
        registered_by: procCook.trim() || null
      });
      showToast(`Merma registrada: ${res.waste_quantity} ${res.unit} (${res.waste_percentage}%)`);
      procGross = '';
      procNet = '';
      procReason = '';
      procCook = '';
    } catch (err) {
      showToast(err.message, true);
    }
  }

  async function handleGeneralWaste(e) {
    e.preventDefault();
    try {
      await InventoryAPI.registerGeneralWaste({
        ingredient_id: genIngId,
        waste_type: genType,
        quantity: parseFloat(genQty),
        reason: genReason.trim() || null
      });
      showToast('Merma directa registrada con éxito');
      genQty = '';
      genReason = '';
    } catch (err) {
      showToast(err.message, true);
    }
  }
</script>

<div class="space-y-6">
  <div>
    <h2 class="text-xl font-bold text-slate-900">Control de Mermas de Cocina</h2>
    <p class="text-sm text-slate-500">Registra el desperdicio operativo y calibración de merma real por insumo</p>
  </div>

  <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
    <!-- MERMA EN PROCESO -->
    <div class="bg-white p-6 rounded-2xl shadow-sm border border-slate-200">
      <div class="flex items-center space-x-2 mb-2">
        <span class="text-xl">🔪</span>
        <h3 class="font-bold text-slate-900 text-base">Merma en Proceso (Limpieza / Pelado)</h3>
      </div>
      <p class="text-xs text-slate-500 mb-4">Calcula la merma real comparando peso bruto contra peso neto aprovechable.</p>

      <form onsubmit={handleProcessWaste} class="space-y-3">
        <div>
          <label class="block text-xs font-semibold text-slate-700 mb-1">Insumo:</label>
          <select bind:value={procIngId} required class="w-full px-3 py-2 border rounded-lg text-sm bg-white">
            <option value="">-- Selecciona Insumo --</option>
            {#each $ingredients as ing}
              <option value={ing.id}>{ing.name} ({ing.unit})</option>
            {/each}
          </select>
        </div>

        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="block text-xs font-semibold text-slate-700 mb-1">Peso Bruto (Inicial):</label>
            <input type="number" step="0.001" bind:value={procGross} required placeholder="0.000" class="w-full px-3 py-2 border rounded-lg text-sm" />
          </div>
          <div>
            <label class="block text-xs font-semibold text-slate-700 mb-1">Peso Neto (Aprovechado):</label>
            <input type="number" step="0.001" bind:value={procNet} required placeholder="0.000" class="w-full px-3 py-2 border rounded-lg text-sm" />
          </div>
        </div>

        <!-- CÁLCULO VISUAL -->
        <div class="bg-slate-50 p-3 rounded-xl border border-slate-200 flex justify-between text-xs">
          <div>
            <span class="text-slate-500">Merma Calculada:</span>
            <span class="font-bold text-slate-800 ml-1">{calcWasteQty}</span>
          </div>
          <div>
            <span class="text-slate-500">Porcentaje:</span>
            <span class="font-bold text-amber-700 ml-1">{calcWastePct}</span>
          </div>
        </div>

        <div>
          <label class="block text-xs font-semibold text-slate-700 mb-1">Cocinero Responsable:</label>
          <input type="text" bind:value={procCook} placeholder="Ej. Alex" class="w-full px-3 py-2 border rounded-lg text-sm" />
        </div>
        <div>
          <label class="block text-xs font-semibold text-slate-700 mb-1">Observaciones:</label>
          <input type="text" bind:value={procReason} placeholder="Cáscara y semillas" class="w-full px-3 py-2 border rounded-lg text-sm" />
        </div>

        <button type="submit" class="w-full bg-black hover:bg-neutral-800 text-white font-bold py-2.5 rounded-xl text-sm transition">
          Registrar Merma Operativa
        </button>
      </form>
    </div>

    <!-- MERMA GENERAL -->
    <div class="bg-white p-6 rounded-2xl shadow-sm border border-slate-200">
      <div class="flex items-center space-x-2 mb-2">
        <span class="text-xl">🗑️</span>
        <h3 class="font-bold text-slate-900 text-base">Merma Directa (Caducidad / Daño)</h3>
      </div>
      <p class="text-xs text-slate-500 mb-4">Descuenta directamente insumos echados a perder o caídos al piso.</p>

      <form onsubmit={handleGeneralWaste} class="space-y-3">
        <div>
          <label class="block text-xs font-semibold text-slate-700 mb-1">Insumo:</label>
          <select bind:value={genIngId} required class="w-full px-3 py-2 border rounded-lg text-sm bg-white">
            <option value="">-- Selecciona Insumo --</option>
            {#each $ingredients as ing}
              <option value={ing.id}>{ing.name} ({ing.unit})</option>
            {/each}
          </select>
        </div>

        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="block text-xs font-semibold text-slate-700 mb-1">Tipo de Merma:</label>
            <select bind:value={genType} class="w-full px-3 py-2 border rounded-lg text-sm bg-white">
              <option value="vida_util">Caducidad / Vida Útil</option>
              <option value="error_humano">Error Humano (Quemado / Caído)</option>
              <option value="falta_calidad">Falta de Calidad / Proveedor</option>
              <option value="rechazo_cliente">Rechazo de Cliente</option>
            </select>
          </div>
          <div>
            <label class="block text-xs font-semibold text-slate-700 mb-1">Cantidad Perdida:</label>
            <input type="number" step="0.001" bind:value={genQty} required placeholder="0.000" class="w-full px-3 py-2 border rounded-lg text-sm" />
          </div>
        </div>

        <div>
          <label class="block text-xs font-semibold text-slate-700 mb-1">Motivo / Razón:</label>
          <input type="text" bind:value={genReason} placeholder="Se rompió el frasco / fecha vencida" class="w-full px-3 py-2 border rounded-lg text-sm" />
        </div>

        <button type="submit" class="w-full bg-rose-600 hover:bg-rose-700 text-white font-bold py-2.5 rounded-xl text-sm transition">
          Descontar por Desperdicio
        </button>
      </form>
    </div>
  </div>
</div>
