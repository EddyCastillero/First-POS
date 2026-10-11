<script>
  import { onMount } from 'svelte';
  import Topbar from './components/Topbar.svelte';
  import Toast from './components/Toast.svelte';
  import PosView from './views/PosView.svelte';
  import InventoryView from './views/InventoryView.svelte';
  import WasteView from './views/WasteView.svelte';
  import RecipesView from './views/RecipesView.svelte';
  import CatalogView from './views/CatalogView.svelte';
  import DailySalesView from './views/DailySalesView.svelte';
  import { currentShift } from './lib/stores.js';
  import { PosAPI } from './lib/api.js';

  let currentRoute = 'caja';

  const ROUTE_MAP = {
    'caja': 'caja',
    'pos': 'caja',
    'inventario': 'inventario',
    'inventory': 'inventario',
    'mermas': 'mermas',
    'waste': 'mermas',
    'recetas': 'recetas',
    'production': 'recetas',
    'catalogo': 'catalogo',
    'menu': 'catalogo',
    'ventas': 'ventas',
    'daily-sales': 'ventas'
  };

  onMount(async () => {
    // 1. Cargar turno de caja activo
    try {
      const shift = await PosAPI.getCurrentShift();
      currentShift.set(shift);
    } catch (err) {
      console.error('Error cargando turno:', err);
    }

    // 2. Escuchar hash en la URL
    syncRouteFromHash();
    window.addEventListener('hashchange', syncRouteFromHash);
    return () => window.removeEventListener('hashchange', syncRouteFromHash);
  });

  function syncRouteFromHash() {
    const hash = window.location.hash.replace('#/', '').replace('#', '').toLowerCase();
    currentRoute = ROUTE_MAP[hash] || 'caja';
  }

  function setRoute(routeId) {
    currentRoute = routeId;
    window.location.hash = `#/${routeId}`;
  }
</script>

<div class="min-h-screen flex flex-col bg-slate-100 text-slate-800">
  <Topbar {currentRoute} {setRoute} />

  <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 flex-1 w-full">
    {#if currentRoute === 'caja'}
      <PosView />
    {:else if currentRoute === 'inventario'}
      <InventoryView />
    {:else if currentRoute === 'mermas'}
      <WasteView />
    {:else if currentRoute === 'recetas'}
      <RecipesView />
    {:else if currentRoute === 'catalogo'}
      <CatalogView />
    {:else if currentRoute === 'ventas'}
      <DailySalesView />
    {/if}
  </main>

  <Toast />
</div>
