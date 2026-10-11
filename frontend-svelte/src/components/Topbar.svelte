<script>
  import { currentShift } from '../lib/stores.js';

  export let currentRoute = 'caja';
  export let setRoute = (r) => {};

  const NAV_ITEMS = [
    { id: 'caja', label: '💳 Caja (POS)' },
    { id: 'inventario', label: '📦 Inventario' },
    { id: 'mermas', label: '🥑 Mermas (Cocina)' },
    { id: 'recetas', label: '📖 Recetas / Subrecetas' },
    { id: 'catalogo', label: '🍔 Catálogo POS' },
    { id: 'ventas', label: '📊 Ventas por Día' }
  ];
</script>

<header class="bg-black text-white shadow-md sticky top-0 z-50">
  <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between border-b border-neutral-800">
    <div class="flex items-center space-x-3">
      <span class="text-2xl">🍔</span>
      <div>
        <h1 class="text-xl font-bold tracking-tight text-white leading-none">First-POS</h1>
        <p class="text-xs text-neutral-400 mt-1">Restaurante & Comedor</p>
      </div>
    </div>

    <!-- BADGE DE ESTADO DEL TURNO -->
    <div>
      {#if $currentShift && $currentShift.status === 'OPEN'}
        <div class="flex items-center space-x-2 bg-emerald-950/60 border border-emerald-500/40 px-3 py-1.5 rounded-full text-xs text-emerald-300">
          <span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
          <span>Turno Abierto: <strong>{$currentShift.cashier_name}</strong></span>
        </div>
      {:else}
        <div class="flex items-center space-x-2 bg-rose-950/60 border border-rose-500/40 px-3 py-1.5 rounded-full text-xs text-rose-300">
          <span class="w-2 h-2 rounded-full bg-rose-400"></span>
          <span>Caja Cerrada</span>
        </div>
      {/if}
    </div>
  </div>

  <!-- NAVEGACIÓN -->
  <div class="bg-neutral-950">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex space-x-2 py-2 overflow-x-auto">
      {#each NAV_ITEMS as item}
        <button
          onclick={() => setRoute(item.id)}
          class="px-4 py-2 rounded-lg text-sm font-semibold transition whitespace-nowrap {currentRoute === item.id ? 'bg-white text-black font-bold shadow-sm' : 'text-neutral-300 hover:text-white hover:bg-neutral-800'}"
        >
          {item.label}
        </button>
      {/each}
    </div>
  </div>
</header>
