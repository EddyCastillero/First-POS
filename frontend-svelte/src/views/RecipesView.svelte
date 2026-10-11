<script>
  import { onMount } from 'svelte';
  import { ingredients, recipes, showToast } from '../lib/stores.js';
  import { InventoryAPI } from '../lib/api.js';

  let currentSubTab = 'main-recipes'; // 'main-recipes' | 'subrecipes'
  let showNewRecipeModal = false;
  let recipeModalType = 'receta';

  // Producción de subreceta
  let prodSubrecipeId = '';
  let prodQty = '';
  let prodNotes = '';
  let prodCook = '';

  // Formulario nueva receta
  let recipeName = '';
  let recipeDesc = '';
  let recipeYieldQty = 1;
  let recipeYieldUnit = 'pza';
  let recipeItems = [];

  $: mainRecipesList = $recipes.filter(r => r.recipe_type === 'receta');
  $: subrecipesList = $recipes.filter(r => r.recipe_type === 'subreceta');

  onMount(async () => {
    await Promise.all([loadRecipes(), loadIngredients()]);
  });

  async function loadRecipes() {
    try {
      const data = await InventoryAPI.getRecipes();
      recipes.set(data);
    } catch (err) {
      console.error(err);
    }
  }

  async function loadIngredients() {
    try {
      const data = await InventoryAPI.getIngredients();
      ingredients.set(data);
    } catch (err) {
      console.error(err);
    }
  }

  function openCreateModal(type) {
    recipeModalType = type;
    recipeName = '';
    recipeDesc = '';
    recipeYieldQty = 1;
    recipeYieldUnit = type === 'receta' ? 'pza' : 'g';
    recipeItems = [];
    addItemRow();
    showNewRecipeModal = true;
  }

  function addItemRow() {
    const defaultTarget = $ingredients.length > 0 ? `ing:${$ingredients[0].id}` : '';
    const defaultUnit = $ingredients.length > 0 ? $ingredients[0].unit : 'g';
    recipeItems = [...recipeItems, { target: defaultTarget, quantity: '', unit: defaultUnit }];
  }

  function handleTargetChange(index, e) {
    const targetVal = e.target.value;
    recipeItems[index].target = targetVal;

    if (targetVal.startsWith('ing:')) {
      const ingId = targetVal.replace('ing:', '');
      const ing = $ingredients.find(i => i.id === ingId);
      if (ing) recipeItems[index].unit = ing.unit;
    } else if (targetVal.startsWith('sub:')) {
      const subId = targetVal.replace('sub:', '');
      const sub = $recipes.find(r => r.id === subId);
      if (sub) recipeItems[index].unit = sub.yield_unit;
    }
  }

  function removeItemRow(index) {
    recipeItems = recipeItems.filter((_, i) => i !== index);
  }

  async function handleCreateRecipe(e) {
    e.preventDefault();
    const items = [];
    for (const item of recipeItems) {
      if (!item.quantity) continue;
      if (item.target.startsWith('ing:')) {
        items.push({ ingredient_id: item.target.replace('ing:', ''), quantity: parseFloat(item.quantity), unit: item.unit });
      } else if (item.target.startsWith('sub:')) {
        items.push({ subrecipe_id: item.target.replace('sub:', ''), quantity: parseFloat(item.quantity), unit: item.unit });
      }
    }

    try {
      const res = await InventoryAPI.createRecipe({
        name: recipeName.trim(),
        recipe_type: recipeModalType,
        description: recipeDesc.trim() || null,
        yield_quantity: parseFloat(recipeYieldQty),
        yield_unit: recipeYieldUnit,
        items
      });
      showToast(`¡Receta "${res.name}" creada con éxito!`);
      showNewRecipeModal = false;
      await loadRecipes();
    } catch (err) {
      showToast(err.message, true);
    }
  }

  async function handleDelete(id, name) {
    if (!confirm(`¿Eliminar la receta "${name}"?`)) return;
    try {
      const res = await InventoryAPI.deleteRecipe(id);
      showToast(res.message || 'Receta eliminada');
      await loadRecipes();
    } catch (err) {
      showToast(err.message, true);
    }
  }

  async function handleProduceSubrecipe(e) {
    e.preventDefault();
    try {
      const res = await InventoryAPI.produceSubrecipe({
        recipe_id: prodSubrecipeId,
        quantity_to_produce: parseFloat(prodQty),
        notes: prodNotes.trim() || null,
        produced_by: prodCook.trim() || null
      });
      showToast(`¡Lote de ${res.quantity_produced} ${res.unit} producido y almacenado!`);
      prodQty = '';
      prodNotes = '';
      prodCook = '';
      await loadIngredients();
    } catch (err) {
      showToast(err.message, true);
    }
  }
</script>

<div>
  <!-- SUB-PESTAÑAS -->
  <div class="flex items-center justify-between mb-6">
    <div class="bg-slate-200 p-1 rounded-xl flex space-x-1">
      <button
        onclick={() => currentSubTab = 'main-recipes'}
        class="px-4 py-2 rounded-lg text-xs font-bold transition {currentSubTab === 'main-recipes' ? 'bg-white text-black shadow-xs' : 'text-slate-600 hover:text-black'}"
      >
        🍽️ Platillos (Recetas Principales)
      </button>
      <button
        onclick={() => currentSubTab = 'subrecipes'}
        class="px-4 py-2 rounded-lg text-xs font-bold transition {currentSubTab === 'subrecipes' ? 'bg-white text-black shadow-xs' : 'text-slate-600 hover:text-black'}"
      >
        🍲 Subrecetas (Mise en Place)
      </button>
    </div>
  </div>

  <!-- VISTA 1: RECETAS PRINCIPALES -->
  {#if currentSubTab === 'main-recipes'}
    <div>
      <div class="flex flex-wrap items-center justify-between gap-4 mb-4">
        <div>
          <h2 class="text-xl font-bold text-slate-900">Recetas de Platillos (Venta)</h2>
          <p class="text-xs text-slate-500">Recetas maestras que descontarán insumos al cobrarse un ticket</p>
        </div>
        <button
          onclick={() => openCreateModal('receta')}
          class="px-4 py-2.5 bg-black hover:bg-neutral-800 text-white text-xs font-bold rounded-xl shadow-sm transition"
        >
          + Nueva Receta de Platillo
        </button>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        {#if mainRecipesList.length === 0}
          <p class="text-xs text-slate-400 italic col-span-2 py-8 text-center bg-white rounded-xl border">No hay recetas de platillos registradas.</p>
        {:else}
          {#each mainRecipesList as r}
            <div class="p-4 rounded-xl border border-slate-100 bg-white hover:border-slate-300 transition shadow-xs flex items-center justify-between">
              <div>
                <h4 class="font-bold text-slate-900 text-sm">{r.name}</h4>
                <p class="text-xs text-slate-500">Porción: {parseFloat(r.yield_quantity)} {r.yield_unit} • {r.items ? r.items.length : 0} componentes</p>
              </div>
              <div class="flex items-center space-x-2">
                <span class="text-xs font-semibold px-2.5 py-1 rounded bg-emerald-100 text-emerald-800">🍽️ Platillo Menú</span>
                <button
                  onclick={() => handleDelete(r.id, r.name)}
                  class="text-rose-500 hover:text-rose-700 hover:bg-rose-50 p-1.5 rounded-lg transition"
                  title="Eliminar receta"
                >
                  🗑️
                </button>
              </div>
            </div>
          {/each}
        {/if}
      </div>
    </div>
  {:else}
    <!-- VISTA 2: SUBRECETAS -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <!-- FORMULARIO PRODUCCIÓN -->
      <div class="bg-white p-6 rounded-2xl shadow-sm border border-slate-200">
        <h3 class="font-bold text-slate-900 text-base mb-1">Registrar Lote de Producción</h3>
        <p class="text-xs text-slate-500 mb-4">Cocina una tanda de salsa o preparación y suma stock listo</p>

        <form onsubmit={handleProduceSubrecipe} class="space-y-3">
          <div>
            <label class="block text-xs font-semibold text-slate-700 mb-1">Subreceta a Preparar:</label>
            <select bind:value={prodSubrecipeId} required class="w-full px-3 py-2 rounded-lg border border-slate-300 text-sm bg-white">
              <option value="">-- Selecciona Subreceta --</option>
              {#each subrecipesList as s}
                <option value={s.id}>{s.name} (Rinde: {parseFloat(s.yield_quantity)} {s.yield_unit})</option>
              {/each}
            </select>
          </div>
          <div>
            <label class="block text-xs font-semibold text-slate-700 mb-1">Cantidad a Producir:</label>
            <input type="number" step="0.001" bind:value={prodQty} required placeholder="Ej. 2000" class="w-full px-3 py-2 rounded-lg border border-slate-300 text-sm" />
          </div>
          <div>
            <label class="block text-xs font-semibold text-slate-700 mb-1">Notas / Lote:</label>
            <input type="text" bind:value={prodNotes} placeholder="Producción matutina" class="w-full px-3 py-2 rounded-lg border border-slate-300 text-sm" />
          </div>
          <div>
            <label class="block text-xs font-semibold text-slate-700 mb-1">Cocinero:</label>
            <input type="text" bind:value={prodCook} placeholder="Ej. Alex" class="w-full px-3 py-2 rounded-lg border border-slate-300 text-sm" />
          </div>
          <button type="submit" class="w-full bg-black hover:bg-neutral-800 text-white font-bold py-2.5 rounded-xl shadow-sm text-sm transition">
            🍲 Ejecutar Producción
          </button>
        </form>
      </div>

      <!-- LISTA DE SUBRECETAS -->
      <div class="lg:col-span-2">
        <div class="bg-white p-6 rounded-2xl shadow-sm border border-slate-200">
          <div class="flex items-center justify-between mb-4 pb-2 border-b">
            <div>
              <h3 class="font-bold text-slate-900 text-base">🍲 Subrecetas en Bodega</h3>
              <p class="text-xs text-slate-500">Preparaciones base (salsas, aderezos, masas)</p>
            </div>
            <button
              onclick={() => openCreateModal('subreceta')}
              class="px-3.5 py-2 bg-black hover:bg-neutral-800 text-white text-xs font-bold rounded-xl shadow-sm transition"
            >
              + Nueva Subreceta
            </button>
          </div>

          <div class="space-y-3">
            {#if subrecipesList.length === 0}
              <p class="text-xs text-slate-400 italic py-6 text-center">No hay subrecetas registradas.</p>
            {:else}
              {#each subrecipesList as s}
                <div class="p-4 rounded-xl border border-slate-100 bg-slate-50 flex items-center justify-between">
                  <div>
                    <h4 class="font-bold text-slate-800 text-sm">{s.name}</h4>
                    <p class="text-xs text-slate-500">Rendimiento: {parseFloat(s.yield_quantity)} {s.yield_unit} • {s.items ? s.items.length : 0} ingredientes</p>
                  </div>
                  <div class="flex items-center space-x-2">
                    <span class="text-xs font-semibold px-2.5 py-1 rounded bg-neutral-200 text-black">Mise en place</span>
                    <button
                      onclick={() => handleDelete(s.id, s.name)}
                      class="text-rose-500 hover:text-rose-700 hover:bg-rose-100/60 p-1.5 rounded-lg transition"
                      title="Eliminar subreceta"
                    >
                      🗑️
                    </button>
                  </div>
                </div>
              {/each}
            {/if}
          </div>
        </div>
      </div>
    </div>
  {/if}
</div>

<!-- MODAL: CREAR RECETA / SUBRECETA -->
{#if showNewRecipeModal}
  <div class="fixed inset-0 bg-slate-900/50 backdrop-blur-sm z-50 flex items-center justify-center p-4 overflow-y-auto">
    <div class="bg-white rounded-2xl shadow-2xl max-w-lg w-full p-6 my-8 max-h-[90vh] flex flex-col">
      <div class="flex items-center justify-between pb-3 border-b mb-4">
        <h3 class="text-lg font-bold text-slate-900">
          {recipeModalType === 'receta' ? 'Crear Receta de Platillo Principal' : 'Crear Subreceta (Mise en Place)'}
        </h3>
        <button type="button" onclick={() => showNewRecipeModal = false} class="text-slate-400 hover:text-slate-600 font-bold text-lg">&times;</button>
      </div>

      <form onsubmit={handleCreateRecipe} class="space-y-4 overflow-y-auto pr-1 flex-1">
        <div>
          <label class="block text-xs font-semibold text-slate-700 mb-1">Nombre:</label>
          <input type="text" bind:value={recipeName} required placeholder="Ej. Tacos de Barbacoa" class="w-full px-3 py-2 border rounded-lg text-sm" />
        </div>
        <div>
          <label class="block text-xs font-semibold text-slate-700 mb-1">Descripción:</label>
          <textarea bind:value={recipeDesc} rows="2" placeholder="Notas sobre la preparación..." class="w-full px-3 py-2 border rounded-lg text-sm"></textarea>
        </div>

        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="block text-xs font-semibold text-slate-700 mb-1">Rendimiento:</label>
            <input type="number" step="0.001" bind:value={recipeYieldQty} required class="w-full px-3 py-2 border rounded-lg text-sm" />
          </div>
          <div>
            <label class="block text-xs font-semibold text-slate-700 mb-1">Unidad:</label>
            <select bind:value={recipeYieldUnit} class="w-full px-3 py-2 border rounded-lg text-sm bg-white">
              <option value="pza">Pieza (pza)</option>
              <option value="g">Gramos (g)</option>
              <option value="ml">Mililitros (ml)</option>
            </select>
          </div>
        </div>

        <!-- LISTA INSUMOS CON UNIDAD BLOQUEADA -->
        <div class="pt-2 border-t">
          <div class="flex items-center justify-between mb-2">
            <span class="text-xs font-bold uppercase tracking-wider text-slate-500">Ingredientes Requeridos</span>
            <button type="button" onclick={addItemRow} class="text-xs bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold px-2 py-1 rounded transition">
              + Agregar Insumo
            </button>
          </div>

          <div class="space-y-2">
            {#each recipeItems as item, i}
              <div class="flex items-center space-x-2 bg-slate-50 p-2 rounded-lg border border-slate-200 text-xs">
                <select
                  value={item.target}
                  onchange={(e) => handleTargetChange(i, e)}
                  class="flex-1 px-2 py-1.5 border rounded bg-white text-xs"
                  required
                >
                  <optgroup label="Insumos Crudos">
                    {#each $ingredients as ing}
                      <option value="ing:{ing.id}">{ing.name} ({ing.unit})</option>
                    {/each}
                  </optgroup>
                  {#if subrecipesList.length > 0}
                    <optgroup label="Subrecetas">
                      {#each subrecipesList as sub}
                        <option value="sub:{sub.id}">{sub.name} ({sub.yield_unit})</option>
                      {/each}
                    </optgroup>
                  {/if}
                </select>

                <input
                  type="number"
                  step="0.001"
                  placeholder="Cant."
                  bind:value={item.quantity}
                  required
                  class="w-24 px-2 py-1.5 border rounded bg-white text-xs font-semibold"
                />

                <!-- UNIDAD INMUTABLE Y FIJA -->
                <span class="w-14 text-center px-2 py-1.5 rounded bg-slate-200 text-slate-700 font-bold text-xs select-none">
                  {item.unit}
                </span>

                <button
                  type="button"
                  onclick={() => removeItemRow(i)}
                  class="text-rose-500 hover:text-rose-700 px-1 font-bold text-sm"
                  title="Quitar"
                >
                  &times;
                </button>
              </div>
            {/each}
          </div>
        </div>

        <div class="flex space-x-3 pt-4 border-t">
          <button type="button" onclick={() => showNewRecipeModal = false} class="w-1/2 py-2 border rounded-lg text-sm font-semibold">Cancelar</button>
          <button type="submit" class="w-1/2 py-2 bg-black text-white rounded-lg text-sm font-bold shadow-sm">Guardar Receta</button>
        </div>
      </form>
    </div>
  </div>
{/if}
