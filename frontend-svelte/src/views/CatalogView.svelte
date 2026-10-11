<script>
  import { onMount } from 'svelte';
  import { menuItems, recipes, showToast } from '../lib/stores.js';
  import { PosAPI, InventoryAPI } from '../lib/api.js';

  let currentFilter = 'active'; // 'active' | 'retired' | 'all'
  let showNewItemModal = false;
  let showReassignModal = false;

  // Formulario nuevo platillo
  let newName = '';
  let newPrice = '';
  let newCategory = '';
  let newRecipeId = '';

  // Modal reasignar receta
  let reassignItemId = '';
  let reassignItemName = '';
  let reassignRecipeId = '';
  let reassignAutoReactivate = true;

  const COMMERCIAL_CATEGORIES = [
    'Desayunos',
    'Comidas',
    'Cenas',
    'Bebidas',
    'Postres',
    'Entradas y Snacks',
    'Adicionales y Extras'
  ];

  $: filteredCatalog = currentFilter === 'active'
    ? $menuItems.filter(m => m.is_active)
    : currentFilter === 'retired'
      ? $menuItems.filter(m => !m.is_active)
      : $menuItems;

  onMount(async () => {
    await Promise.all([loadCatalog(), loadRecipes()]);
  });

  async function loadCatalog() {
    try {
      const data = await PosAPI.getMenuItems(false);
      menuItems.set(data);
    } catch (err) {
      console.error(err);
    }
  }

  async function loadRecipes() {
    try {
      const data = await InventoryAPI.getRecipes();
      recipes.set(data);
    } catch (err) {
      console.error(err);
    }
  }

  async function handleCreateItem(e) {
    e.preventDefault();
    try {
      const res = await PosAPI.createMenuItem({
        name: newName.trim(),
        price: parseFloat(newPrice),
        category: newCategory || null,
        recipe_id: newRecipeId
      });
      showToast(`Platillo "${res.name}" agregado al menú`);
      showNewItemModal = false;
      newName = '';
      newPrice = '';
      newCategory = '';
      newRecipeId = '';
      await loadCatalog();
    } catch (err) {
      showToast(err.message, true);
    }
  }

  async function handleDelete(id, name) {
    if (!confirm(`¿Retirar "${name}" del menú de venta?`)) return;
    try {
      const res = await PosAPI.deleteMenuItem(id);
      showToast(res.message || 'Platillo retirado');
      await loadCatalog();
    } catch (err) {
      showToast(err.message, true);
    }
  }

  async function handleReactivate(id, name) {
    try {
      const res = await PosAPI.reactivateMenuItem(id);
      showToast(res.message || `Platillo "${name}" reactivado`);
      await loadCatalog();
    } catch (err) {
      showToast(err.message, true);
    }
  }

  function openReassign(item) {
    reassignItemId = item.id;
    reassignItemName = item.name;
    reassignRecipeId = '';
    reassignAutoReactivate = true;
    showReassignModal = true;
  }

  async function handleReassign(e) {
    e.preventDefault();
    try {
      await PosAPI.updateMenuItem(reassignItemId, { recipe_id: reassignRecipeId });
      if (reassignAutoReactivate) {
        await PosAPI.reactivateMenuItem(reassignItemId);
      }
      showToast(`¡Receta vinculada y platillo '${reassignItemName}' listo!`);
      showReassignModal = false;
      await loadCatalog();
    } catch (err) {
      showToast(err.message, true);
    }
  }
</script>

<div>
  <!-- CABECERA Y FILTROS -->
  <div class="flex flex-wrap items-center justify-between gap-4 mb-6">
    <div>
      <h2 class="text-xl font-bold text-slate-900">Catálogo de Productos y Platillos (POS)</h2>
      <p class="text-sm text-slate-500">Configura los productos que se venden en Caja, sus precios y la receta técnica que descuentan.</p>
    </div>
    <div class="flex items-center space-x-3">
      <!-- PÍLDORAS FILTRO -->
      <div class="bg-slate-200 p-1 rounded-xl flex space-x-1 text-xs">
        <button
          onclick={() => currentFilter = 'active'}
          class="px-3 py-1.5 rounded-lg font-bold transition {currentFilter === 'active' ? 'bg-white text-black shadow-xs' : 'text-slate-600 hover:text-black'}"
        >
          🟢 Activos en Caja
        </button>
        <button
          onclick={() => currentFilter = 'retired'}
          class="px-3 py-1.5 rounded-lg font-semibold transition {currentFilter === 'retired' ? 'bg-white text-black shadow-xs' : 'text-slate-600 hover:text-black'}"
        >
          ⚪ Retirados / Históricos
        </button>
        <button
          onclick={() => currentFilter = 'all'}
          class="px-3 py-1.5 rounded-lg font-semibold transition {currentFilter === 'all' ? 'bg-white text-black shadow-xs' : 'text-slate-600 hover:text-black'}"
        >
          Todos
        </button>
      </div>

      <button
        onclick={() => showNewItemModal = true}
        class="px-4 py-2.5 bg-black hover:bg-neutral-800 text-white text-xs font-bold rounded-xl shadow-sm transition"
      >
        + Nuevo Platillo al Menú
      </button>
    </div>
  </div>

  <!-- TABLA CATÁLOGO -->
  <div class="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
    <div class="overflow-x-auto">
      <table class="min-w-full divide-y divide-slate-200 text-left text-sm">
        <thead class="bg-slate-50 text-slate-500 text-xs uppercase font-semibold">
          <tr>
            <th class="px-6 py-3.5">Platillo de Venta</th>
            <th class="px-6 py-3.5">Categoría</th>
            <th class="px-6 py-3.5">Precio de Venta</th>
            <th class="px-6 py-3.5">Receta de Cocina Vinculada</th>
            <th class="px-6 py-3.5">Estado en Caja</th>
            <th class="px-6 py-3.5 text-center">Acciones</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-slate-100">
          {#if filteredCatalog.length === 0}
            <tr>
              <td colspan="6" class="px-6 py-8 text-center text-slate-400 italic">
                {currentFilter === 'active' ? 'No hay platillos activos a la venta.' : currentFilter === 'retired' ? 'No hay platillos retirados en archivo.' : 'No hay platillos registrados en el menú.'}
              </td>
            </tr>
          {:else}
            {#each filteredCatalog as item}
              {@const recipe = $recipes.find(r => r.id === item.recipe_id)}
              <tr class="hover:bg-slate-50 transition {item.is_active ? '' : 'bg-slate-50/40 opacity-75'}">
                <td class="px-6 py-3.5 font-bold text-slate-900">{item.name}</td>
                <td class="px-6 py-3.5 text-slate-500">{item.category || '-'}</td>
                <td class="px-6 py-3.5 font-extrabold text-slate-900">${parseFloat(item.price).toFixed(2)}</td>
                <td class="px-6 py-3.5">
                  {#if recipe}
                    <span class="inline-flex items-center px-2.5 py-1 rounded-md text-xs font-semibold bg-neutral-100 text-neutral-800 border border-neutral-200">
                      🍳 {recipe.name}
                    </span>
                  {:else}
                    <span class="inline-flex items-center px-2.5 py-1 rounded-md text-xs font-semibold bg-amber-50 text-amber-800 border border-amber-200">
                      ⚠️ Sin Receta Activa
                    </span>
                  {/if}
                </td>
                <td class="px-6 py-3.5">
                  {#if item.is_active}
                    <span class="inline-flex items-center px-2.5 py-1 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-800">🟢 Activo en Caja</span>
                  {:else if !recipe}
                    <span class="inline-flex items-center px-2.5 py-1 rounded-full text-[10px] font-bold bg-slate-100 text-slate-500 border border-slate-200">⚪ Histórico (Sin receta)</span>
                  {:else}
                    <span class="inline-flex items-center px-2.5 py-1 rounded-full text-[10px] font-bold bg-slate-200 text-slate-600">⚪ Retirado de Caja</span>
                  {/if}
                </td>
                <td class="px-6 py-3.5 text-center">
                  {#if item.is_active}
                    <button
                      onclick={() => handleDelete(item.id, item.name)}
                      class="text-rose-500 hover:text-rose-700 hover:bg-rose-50 px-2.5 py-1 rounded-lg text-xs font-semibold transition"
                    >
                      🗑️ Retirar
                    </button>
                  {:else if !recipe}
                    <button
                      onclick={() => openReassign(item)}
                      class="px-2.5 py-1 text-xs font-bold bg-black hover:bg-neutral-800 text-white rounded-lg transition"
                    >
                      🔗 Asignar Receta
                    </button>
                  {:else}
                    <div class="flex items-center justify-center space-x-1.5">
                      <button
                        onclick={() => handleReactivate(item.id, item.name)}
                        class="px-2.5 py-1 text-xs font-bold bg-emerald-100 hover:bg-emerald-200 text-emerald-800 rounded-lg transition"
                      >
                        ♻️ Reactivar
                      </button>
                      <button
                        onclick={() => openReassign(item)}
                        class="px-2 py-1 text-xs text-slate-500 hover:text-slate-800 hover:bg-slate-100 rounded-lg transition"
                        title="Cambiar receta vinculada"
                      >
                        ✏️
                      </button>
                    </div>
                  {/if}
                </td>
              </tr>
            {/each}
          {/if}
        </tbody>
      </table>
    </div>
  </div>
</div>

<!-- MODAL: NUEVO PLATILLO AL MENÚ -->
{#if showNewItemModal}
  <div class="fixed inset-0 bg-slate-900/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
    <div class="bg-white rounded-2xl shadow-2xl max-w-md w-full p-6">
      <div class="flex items-center justify-between pb-3 border-b mb-4">
        <h3 class="text-lg font-bold text-slate-900">Dar de Alta Platillo en el Menú</h3>
        <button type="button" onclick={() => showNewItemModal = false} class="text-slate-400 hover:text-slate-600 font-bold text-lg">&times;</button>
      </div>

      <form onsubmit={handleCreateItem} class="space-y-4">
        <div>
          <label class="block text-xs font-semibold text-slate-700 mb-1">Nombre Comercial en Caja:</label>
          <input type="text" bind:value={newName} required placeholder="Ej. Orden de Chilaquiles Verdes" class="w-full px-3 py-2 border rounded-lg text-sm" />
        </div>

        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="block text-xs font-semibold text-slate-700 mb-1">Precio al Público ($):</label>
            <input type="number" step="0.01" bind:value={newPrice} required placeholder="125.00" class="w-full px-3 py-2 border rounded-lg text-sm font-semibold" />
          </div>
          <div>
            <label class="block text-xs font-semibold text-slate-700 mb-1">Categoría:</label>
            <select bind:value={newCategory} required class="w-full px-3 py-2 border rounded-lg text-sm bg-white font-medium">
              <option value="">-- Selecciona --</option>
              {#each COMMERCIAL_CATEGORIES as cat}
                <option value={cat}>{cat}</option>
              {/each}
            </select>
          </div>
        </div>

        <div>
          <label class="block text-xs font-semibold text-slate-700 mb-1">Receta Culinaria Vinculada:</label>
          <select bind:value={newRecipeId} required class="w-full px-3 py-2 border rounded-lg text-sm bg-white">
            <option value="">-- Selecciona una Receta --</option>
            {#each $recipes as r}
              <option value={r.id}>[{r.recipe_type === 'receta' ? 'Platillo' : 'Subreceta'}] {r.name}</option>
            {/each}
          </select>
        </div>

        <div class="flex space-x-3 pt-3 border-t">
          <button type="button" onclick={() => showNewItemModal = false} class="w-1/2 py-2 border rounded-lg text-sm font-semibold">Cancelar</button>
          <button type="submit" class="w-1/2 py-2 bg-black text-white rounded-lg text-sm font-bold shadow-sm">Agregar al Menú</button>
        </div>
      </form>
    </div>
  </div>
{/if}

<!-- MODAL: ASIGNAR RECETA -->
{#if showReassignModal}
  <div class="fixed inset-0 bg-slate-900/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
    <div class="bg-white rounded-2xl shadow-2xl max-w-md w-full p-6">
      <div class="flex items-center justify-between pb-3 border-b mb-4">
        <div>
          <h3 class="text-base font-bold text-slate-900">Asignar Receta al Platillo</h3>
          <p class="text-xs text-slate-500 font-semibold">{reassignItemName}</p>
        </div>
        <button type="button" onclick={() => showReassignModal = false} class="text-slate-400 hover:text-slate-600 font-bold text-lg">&times;</button>
      </div>

      <form onsubmit={handleReassign} class="space-y-4">
        <div>
          <label class="block text-xs font-semibold text-slate-700 mb-1">Selecciona la Receta Técnica:</label>
          <select bind:value={reassignRecipeId} required class="w-full px-3 py-2 border rounded-lg text-sm bg-white">
            <option value="">-- Selecciona una Receta --</option>
            {#each $recipes as r}
              <option value={r.id}>[{r.recipe_type === 'receta' ? 'Platillo' : 'Subreceta'}] {r.name}</option>
            {/each}
          </select>
        </div>

        <div class="flex items-center space-x-2 pt-1">
          <input type="checkbox" id="reassign-auto" bind:checked={reassignAutoReactivate} class="rounded border-slate-300 text-black focus:ring-black" />
          <label for="reassign-auto" class="text-xs text-slate-700 font-medium">Reactivar en Caja tras vincular</label>
        </div>

        <div class="flex space-x-3 pt-3 border-t">
          <button type="button" onclick={() => showReassignModal = false} class="w-1/2 py-2 border rounded-lg text-sm font-semibold">Cancelar</button>
          <button type="submit" class="w-1/2 py-2 bg-black text-white rounded-lg text-sm font-bold shadow-sm">Vincular y Guardar</button>
        </div>
      </form>
    </div>
  </div>
{/if}
