<script>
  import { onMount } from 'svelte';
  import { ingredients, showToast } from '../lib/stores.js';
  import { InventoryAPI } from '../lib/api.js';

  let selectedFilter = 'ALL';
  let showNewModal = false;
  let showEntryModal = false;

  // Formulario nuevo insumo
  let newName = '';
  let newCat = '';
  let newUnit = 'g';
  let newInitialStock = 0;
  let newMinStock = 0;

  // Formulario entrada stock
  let entryIngId = '';
  let entryQty = '';
  let entryCost = '';
  let entryNote = '';

  const CATEGORIES = [
    'Lácteos y derivados',
    'Carnes',
    'Pescados y mariscos',
    'Verduras y hortalizas',
    'Frutas',
    'Cereales y granos',
    'Leguminosas',
    'Harinas y almidones',
    'Aceites y grasas vegetales',
    'Endulzantes y conservas',
    'Especias secas y hierbas frescas',
    'Salsas base, vinagres y caldos',
    'Sal, azúcares y condimentos'
  ];

  $: filteredIngredients = selectedFilter === 'ALL'
    ? $ingredients
    : selectedFilter === 'OTRAS'
      ? $ingredients.filter(i => !i.category || i.category.trim() === '')
      : $ingredients.filter(i => i.category === selectedFilter);

  onMount(async () => {
    await loadIngredients();
  });

  async function loadIngredients() {
    try {
      const data = await InventoryAPI.getIngredients();
      ingredients.set(data);
    } catch (err) {
      console.error(err);
    }
  }

  async function handleCreateIngredient(e) {
    e.preventDefault();
    try {
      const res = await InventoryAPI.createIngredient({
        name: newName.trim(),
        category: newCat || null,
        unit: newUnit,
        initial_stock: parseFloat(newInitialStock) || 0,
        min_stock: parseFloat(newMinStock) || 0
      });
      showToast(`Insumo '${res.name}' dado de alta`);
      showNewModal = false;
      newName = '';
      newCat = '';
      newInitialStock = 0;
      newMinStock = 0;
      await loadIngredients();
    } catch (err) {
      showToast(err.message, true);
    }
  }

  async function handleStockEntry(e) {
    e.preventDefault();
    try {
      await InventoryAPI.addStockEntry({
        ingredient_id: entryIngId,
        quantity: parseFloat(entryQty),
        cost_per_unit: entryCost ? parseFloat(entryCost) : null,
        note: entryNote.trim() || null
      });
      showToast('Stock añadido con éxito');
      showEntryModal = false;
      entryQty = '';
      entryCost = '';
      entryNote = '';
      await loadIngredients();
    } catch (err) {
      showToast(err.message, true);
    }
  }

  async function handleDelete(id, name) {
    if (!confirm(`¿Eliminar insumo "${name}"?`)) return;
    try {
      const res = await InventoryAPI.deleteIngredient(id);
      showToast(res.message || 'Insumo eliminado');
      await loadIngredients();
    } catch (err) {
      showToast(err.message, true);
    }
  }
</script>

<div>
  <!-- CABECERA -->
  <div class="flex flex-wrap items-center justify-between gap-4 mb-6">
    <div>
      <h2 class="text-xl font-bold text-slate-900">Almacén de Insumos</h2>
      <p class="text-sm text-slate-500">Control de materias primas, unidades y stock en bodega</p>
    </div>
    <div class="flex items-center space-x-3">
      <!-- FILTRO CATEGORÍA -->
      <div class="flex items-center space-x-2 bg-white px-3 py-1.5 rounded-xl border border-slate-200 shadow-2xs">
        <label for="inv-cat-filter" class="text-xs font-semibold text-slate-500 whitespace-nowrap">Filtrar por:</label>
        <select
          id="inv-cat-filter"
          bind:value={selectedFilter}
          class="text-xs font-bold text-slate-800 bg-transparent border-none focus:ring-0 pr-6"
        >
          <option value="ALL">Todas las Categorías</option>
          {#each CATEGORIES as cat}
            <option value={cat}>{cat}</option>
          {/each}
          <option value="OTRAS">Otras / Sin Categoría</option>
        </select>
      </div>

      <button
        onclick={() => showNewModal = true}
        class="px-4 py-2 bg-black hover:bg-neutral-800 text-white text-xs font-bold rounded-xl shadow-sm transition"
      >
        + Nuevo Insumo
      </button>
      <button
        onclick={() => showEntryModal = true}
        class="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold rounded-xl shadow-sm transition"
      >
        📥 Entrada de Stock
      </button>
    </div>
  </div>

  <!-- TABLA DE INVENTARIO -->
  <div class="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
    <div class="overflow-x-auto">
      <table class="min-w-full divide-y divide-slate-200 text-left text-sm">
        <thead class="bg-slate-50 text-slate-500 text-xs uppercase font-semibold">
          <tr>
            <th class="px-6 py-3.5">Insumo</th>
            <th class="px-6 py-3.5">Categoría</th>
            <th class="px-6 py-3.5">Stock Actual</th>
            <th class="px-6 py-3.5">Stock Mínimo</th>
            <th class="px-6 py-3.5">Costo Unitario</th>
            <th class="px-6 py-3.5">Merma Est.</th>
            <th class="px-6 py-3.5">Estado</th>
            <th class="px-6 py-3.5 text-center">Acciones</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-slate-100">
          {#if filteredIngredients.length === 0}
            <tr>
              <td colspan="8" class="px-6 py-8 text-center text-slate-400 italic">
                {selectedFilter === 'ALL' ? 'No hay insumos registrados en bodega.' : `No hay insumos en la categoría "${selectedFilter}".`}
              </td>
            </tr>
          {:else}
            {#each filteredIngredients as ing}
              {@const cur = parseFloat(ing.current_stock)}
              {@const min = parseFloat(ing.min_stock)}
              <tr class="hover:bg-slate-50 transition">
                <td class="px-6 py-3 font-semibold text-slate-900">{ing.name}</td>
                <td class="px-6 py-3">
                  {#if ing.category}
                    <span class="inline-flex items-center px-2 py-0.5 rounded-md text-xs font-semibold bg-slate-100 text-slate-700 border border-slate-200">{ing.category}</span>
                  {:else}
                    <span class="text-xs text-slate-400 italic">Sin categoría</span>
                  {/if}
                </td>
                <td class="px-6 py-3 font-bold text-slate-900">{cur.toFixed(2)} <span class="text-xs font-normal text-slate-400">{ing.unit}</span></td>
                <td class="px-6 py-3 text-slate-500">{min.toFixed(2)} {ing.unit}</td>
                <td class="px-6 py-3 text-slate-600">{ing.cost_per_unit ? `$${parseFloat(ing.cost_per_unit).toFixed(2)}` : '-'}</td>
                <td class="px-6 py-3 text-slate-500">{parseFloat(ing.waste_percentage).toFixed(1)}%</td>
                <td class="px-6 py-3">
                  {#if cur <= 0}
                    <span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-rose-100 text-rose-800">🔴 Agotado</span>
                  {:else if cur <= min}
                    <span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-100 text-amber-800">🟡 Stock Bajo</span>
                  {:else}
                    <span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-800">🟢 Óptimo</span>
                  {/if}
                </td>
                <td class="px-6 py-3 text-center">
                  <button
                    onclick={() => handleDelete(ing.id, ing.name)}
                    class="text-rose-500 hover:text-rose-700 hover:bg-rose-50 p-1.5 rounded-lg transition"
                    title="Eliminar insumo"
                  >
                    🗑️
                  </button>
                </td>
              </tr>
            {/each}
          {/if}
        </tbody>
      </table>
    </div>
  </div>
</div>

<!-- MODAL: NUEVO INSUMO -->
{#if showNewModal}
  <div class="fixed inset-0 bg-slate-900/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
    <div class="bg-white rounded-2xl shadow-2xl max-w-md w-full p-6">
      <h3 class="text-lg font-bold text-slate-900 mb-3">Dar de Alta Nuevo Insumo</h3>
      <form onsubmit={handleCreateIngredient} class="space-y-3">
        <div>
          <label class="block text-xs font-medium text-slate-700 mb-1">Nombre:</label>
          <input type="text" bind:value={newName} required placeholder="Ej. Queso Gouda" class="w-full px-3 py-2 border rounded-lg text-sm" />
        </div>
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="block text-xs font-medium text-slate-700 mb-1">Categoría:</label>
            <select bind:value={newCat} required class="w-full px-3 py-2 border rounded-lg text-sm bg-white">
              <option value="">-- Selecciona --</option>
              {#each CATEGORIES as cat}
                <option value={cat}>{cat}</option>
              {/each}
            </select>
          </div>
          <div>
            <label class="block text-xs font-medium text-slate-700 mb-1">Unidad Base:</label>
            <select bind:value={newUnit} class="w-full px-3 py-2 border rounded-lg text-sm bg-white">
              <option value="g">Gramos (g)</option>
              <option value="ml">Mililitros (ml)</option>
              <option value="pza">Piezas (pza)</option>
            </select>
          </div>
        </div>
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="block text-xs font-medium text-slate-700 mb-1">Stock Inicial:</label>
            <input type="number" step="0.001" bind:value={newInitialStock} class="w-full px-3 py-2 border rounded-lg text-sm" />
          </div>
          <div>
            <label class="block text-xs font-medium text-slate-700 mb-1">Stock Mínimo:</label>
            <input type="number" step="0.001" bind:value={newMinStock} class="w-full px-3 py-2 border rounded-lg text-sm" />
          </div>
        </div>
        <div class="flex space-x-3 pt-3">
          <button type="button" onclick={() => showNewModal = false} class="w-1/2 py-2 border rounded-lg text-sm">Cancelar</button>
          <button type="submit" class="w-1/2 py-2 bg-black text-white rounded-lg text-sm font-semibold">Guardar</button>
        </div>
      </form>
    </div>
  </div>
{/if}

<!-- MODAL: ENTRADA DE STOCK -->
{#if showEntryModal}
  <div class="fixed inset-0 bg-slate-900/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
    <div class="bg-white rounded-2xl shadow-2xl max-w-md w-full p-6">
      <h3 class="text-lg font-bold text-slate-900 mb-3">Entrada Manual de Stock</h3>
      <form onsubmit={handleStockEntry} class="space-y-3">
        <div>
          <label class="block text-xs font-medium text-slate-700 mb-1">Insumo:</label>
          <select bind:value={entryIngId} required class="w-full px-3 py-2 border rounded-lg text-sm bg-white">
            <option value="">-- Selecciona Insumo --</option>
            {#each $ingredients as ing}
              <option value={ing.id}>{ing.name} (Stock: {parseFloat(ing.current_stock)} {ing.unit})</option>
            {/each}
          </select>
        </div>
        <div>
          <label class="block text-xs font-medium text-slate-700 mb-1">Cantidad:</label>
          <input type="number" step="0.001" bind:value={entryQty} required placeholder="Ej. 1000" class="w-full px-3 py-2 border rounded-lg text-sm" />
        </div>
        <div>
          <label class="block text-xs font-medium text-slate-700 mb-1">Costo Unitario (Opcional):</label>
          <input type="number" step="0.01" bind:value={entryCost} placeholder="0.00" class="w-full px-3 py-2 border rounded-lg text-sm" />
        </div>
        <div>
          <label class="block text-xs font-medium text-slate-700 mb-1">Nota / Proveedor:</label>
          <input type="text" bind:value={entryNote} placeholder="Compra en central de abastos" class="w-full px-3 py-2 border rounded-lg text-sm" />
        </div>
        <div class="flex space-x-3 pt-3">
          <button type="button" onclick={() => showEntryModal = false} class="w-1/2 py-2 border rounded-lg text-sm">Cancelar</button>
          <button type="submit" class="w-1/2 py-2 bg-emerald-600 text-white rounded-lg text-sm font-semibold">Cargar Stock</button>
        </div>
      </form>
    </div>
  </div>
{/if}
