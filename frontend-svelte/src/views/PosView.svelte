<script>
  import { onMount } from 'svelte';
  import { currentShift, cart, menuItems, showToast } from '../lib/stores.js';
  import { PosAPI } from '../lib/api.js';

  let openCashierName = '';
  let openInitialCash = 1000;
  let closeActualCash = '';
  let closeNotes = '';
  let showCloseModal = false;

  let selectedCategory = 'ALL';
  let paymentMethod = 'CASH';
  let cashGiven = '';

  $: totalAmount = $cart.reduce((sum, item) => sum + (item.price * item.quantity), 0);
  $: changeAmount = (paymentMethod === 'CASH' && parseFloat(cashGiven) >= totalAmount)
    ? (parseFloat(cashGiven) - totalAmount).toFixed(2)
    : '0.00';

  $: categories = ['ALL', ...Array.from(new Set($menuItems.map(m => m.category || 'General').filter(Boolean)))];
  $: filteredMenuItems = selectedCategory === 'ALL'
    ? $menuItems
    : $menuItems.filter(m => (m.category || 'General') === selectedCategory);

  onMount(async () => {
    await loadMenu();
  });

  async function loadMenu() {
    try {
      const items = await PosAPI.getMenuItems(true);
      menuItems.set(items);
    } catch (err) {
      console.error(err);
    }
  }

  async function handleOpenShift(e) {
    e.preventDefault();
    try {
      const shift = await PosAPI.openShift(openCashierName, openInitialCash);
      currentShift.set(shift);
      showToast(`Turno abierto con éxito para ${shift.cashier_name}`);
    } catch (err) {
      showToast(err.message, true);
    }
  }

  async function handleCloseShift(e) {
    e.preventDefault();
    if (!$currentShift) return;
    try {
      const res = await PosAPI.closeShift($currentShift.id, parseFloat(closeActualCash), closeNotes);
      showToast(`Turno cerrado. Diferencia: $${parseFloat(res.difference).toFixed(2)}`);
      currentShift.set(null);
      showCloseModal = false;
    } catch (err) {
      showToast(err.message, true);
    }
  }

  function addToCart(item) {
    cart.update(items => {
      const existing = items.find(i => i.menu_item_id === item.id);
      if (existing) {
        existing.quantity += 1;
        return [...items];
      }
      return [...items, { menu_item_id: item.id, name: item.name, price: parseFloat(item.price), quantity: 1 }];
    });
  }

  function updateQty(index, delta) {
    cart.update(items => {
      items[index].quantity += delta;
      if (items[index].quantity <= 0) {
        items.splice(index, 1);
      }
      return [...items];
    });
  }

  function clearCart() {
    cart.set([]);
    cashGiven = '';
  }

  async function handleCheckout() {
    if ($cart.length === 0) return;
    if (paymentMethod === 'CASH') {
      const given = parseFloat(cashGiven);
      if (!given || given < totalAmount) {
        showToast(`El efectivo entregado ($${given || 0}) debe cubrir el total ($${totalAmount.toFixed(2)})`, true);
        return;
      }
    }

    const payload = {
      items: $cart.map(c => ({ menu_item_id: c.menu_item_id, quantity: c.quantity })),
      payment_method: paymentMethod,
      cash_given: paymentMethod === 'CASH' ? parseFloat(cashGiven) : null
    };

    try {
      const res = await PosAPI.checkout(payload);
      showToast(`¡Venta cobrada con éxito! Folio: ${res.order_number}`);
      clearCart();
      const shift = await PosAPI.getCurrentShift();
      currentShift.set(shift);
    } catch (err) {
      showToast(err.message, true);
    }
  }
</script>

<div>
  <!-- CAJA CERRADA -->
  {#if !$currentShift || $currentShift.status !== 'OPEN'}
    <div class="bg-white p-8 rounded-2xl shadow-sm border border-slate-200 max-w-xl mx-auto text-center mt-6">
      <div class="w-16 h-16 bg-amber-100 text-amber-600 rounded-full flex items-center justify-center mx-auto mb-4 text-3xl">
        🔒
      </div>
      <h2 class="text-2xl font-bold text-slate-900 mb-2">Caja Registradora Cerrada</h2>
      <p class="text-slate-600 text-sm mb-6">Para empezar a cobrar órdenes, debes realizar la apertura del turno con un fondo de caja fijo.</p>

      <form onsubmit={handleOpenShift} class="text-left space-y-4">
        <div>
          <label class="block text-sm font-medium text-slate-700 mb-1">Nombre del Cajero:</label>
          <input
            type="text"
            bind:value={openCashierName}
            required
            placeholder="Ej. Leonel"
            class="w-full px-4 py-2.5 rounded-lg border border-slate-300 focus:ring-2 focus:ring-black text-sm"
          />
        </div>

        <div>
          <label class="block text-sm font-medium text-slate-700 mb-2">Selecciona Fondo Fijo para Cambio:</label>
          <div class="grid grid-cols-3 gap-3">
            {#each [1000, 2000, 3000] as amount}
              <button
                type="button"
                onclick={() => openInitialCash = amount}
                class="border-2 rounded-xl p-3 text-center transition {openInitialCash === amount ? 'border-black bg-neutral-100' : 'border-slate-200 hover:border-black'}"
              >
                <span class="block text-xs font-semibold text-slate-500">{amount === 1000 ? 'Básico' : amount === 2000 ? 'Estándar' : 'Alto Flujo'}</span>
                <span class="text-lg font-bold text-slate-900">${amount.toLocaleString()}</span>
              </button>
            {/each}
          </div>
        </div>

        <button type="submit" class="w-full mt-4 bg-black hover:bg-neutral-800 text-white font-semibold py-3 px-4 rounded-xl shadow transition">
          🔓 Abrir Turno de Caja
        </button>
      </form>
    </div>
  {:else}
    <!-- CAJA ABIERTA -->
    <div>
      <!-- RESUMEN DEL TURNO -->
      <div class="bg-white p-4 rounded-xl shadow-sm border border-slate-200 mb-6 flex flex-wrap items-center justify-between gap-4">
        <div class="flex items-center space-x-6">
          <div>
            <span class="text-xs text-slate-500 uppercase font-semibold">Cajero</span>
            <p class="font-bold text-slate-900 text-base">{$currentShift.cashier_name}</p>
          </div>
          <div>
            <span class="text-xs text-slate-500 uppercase font-semibold">Fondo Inicial</span>
            <p class="font-bold text-slate-900 text-base">${parseFloat($currentShift.initial_cash).toFixed(2)}</p>
          </div>
          <div>
            <span class="text-xs text-slate-500 uppercase font-semibold">Ventas Efectivo</span>
            <p class="font-bold text-emerald-600 text-base">${parseFloat($currentShift.cash_sales_total).toFixed(2)}</p>
          </div>
          <div>
            <span class="text-xs text-slate-500 uppercase font-semibold">Efectivo Esperado</span>
            <p class="font-bold text-black text-base">${parseFloat($currentShift.expected_cash).toFixed(2)}</p>
          </div>
        </div>
        <button
          onclick={() => showCloseModal = true}
          class="px-4 py-2 bg-rose-50 text-rose-700 hover:bg-rose-100 border border-rose-200 rounded-lg text-sm font-semibold transition"
        >
          🔒 Cerrar Turno (Arqueo)
        </button>
      </div>

      <!-- INTERFAZ PRINCIPAL -->
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <!-- MENÚ Y CATEGORÍAS -->
        <div class="lg:col-span-2">
          <div class="flex flex-wrap items-center justify-between gap-3 mb-4">
            <div>
              <h2 class="text-lg font-bold text-slate-900">Menú de Platillos</h2>
              <span class="text-xs text-slate-500">Selecciona para agregar a la orden</span>
            </div>
            <!-- Filtro de Categorías -->
            <div class="flex flex-wrap gap-1.5 text-xs">
              {#each categories as cat}
                <button
                  onclick={() => selectedCategory = cat}
                  class="px-2.5 py-1 rounded-lg font-bold transition {selectedCategory === cat ? 'bg-black text-white' : 'bg-slate-200 text-slate-700 hover:bg-slate-300'}"
                >
                  {cat === 'ALL' ? 'Todos' : cat}
                </button>
              {/each}
            </div>
          </div>

          <div class="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
            {#if filteredMenuItems.length === 0}
              <p class="text-sm text-slate-400 col-span-3 text-center py-8">No hay platillos en esta categoría.</p>
            {:else}
              {#each filteredMenuItems as item}
                <div class="bg-white p-4 rounded-xl border border-slate-200 hover:border-black transition shadow-sm flex flex-col justify-between">
                  <div>
                    <span class="text-[10px] font-bold uppercase tracking-wider text-slate-400 bg-slate-100 px-2 py-0.5 rounded">{item.category || 'General'}</span>
                    <h4 class="font-bold text-slate-800 text-sm mt-1.5">{item.name}</h4>
                    <p class="text-black font-extrabold text-lg mt-1">${parseFloat(item.price).toFixed(2)}</p>
                  </div>
                  <button
                    onclick={() => addToCart(item)}
                    class="mt-3 w-full bg-slate-900 hover:bg-black text-white font-semibold py-1.5 px-3 rounded-lg text-xs transition"
                  >
                    + Agregar
                  </button>
                </div>
              {/each}
            {/if}
          </div>
        </div>

        <!-- TICKET DE COBRO -->
        <div class="lg:col-span-1">
          <div class="bg-white rounded-2xl shadow-sm border border-slate-200 p-5 sticky top-24">
            <div class="flex items-center justify-between pb-3 border-b border-slate-100 mb-4">
              <h3 class="font-bold text-slate-900 text-base">Ticket de Orden</h3>
              <button onclick={clearCart} class="text-xs text-slate-400 hover:text-rose-600">Vaciar</button>
            </div>

            <!-- ITEMS EN TICKET -->
            <div class="space-y-3 max-h-60 overflow-y-auto mb-4">
              {#if $cart.length === 0}
                <p class="text-xs text-slate-400 text-center py-6">El ticket está vacío. Agrega platillos del menú.</p>
              {:else}
                {#each $cart as c, i}
                  <div class="flex items-center justify-between text-xs">
                    <div class="flex-1 pr-2">
                      <p class="font-bold text-slate-800">{c.name}</p>
                      <p class="text-slate-400">${c.price.toFixed(2)} c/u</p>
                    </div>
                    <div class="flex items-center space-x-2">
                      <button onclick={() => updateQty(i, -1)} class="w-6 h-6 rounded bg-slate-100 hover:bg-slate-200 text-slate-700 font-bold flex items-center justify-center">-</button>
                      <span class="font-bold text-slate-800 w-4 text-center">{c.quantity}</span>
                      <button onclick={() => updateQty(i, 1)} class="w-6 h-6 rounded bg-slate-100 hover:bg-slate-200 text-slate-700 font-bold flex items-center justify-center">+</button>
                    </div>
                    <span class="font-bold text-slate-900 ml-3">${(c.price * c.quantity).toFixed(2)}</span>
                  </div>
                {/each}
              {/if}
            </div>

            <!-- TOTAL -->
            <div class="border-t border-slate-100 pt-3 space-y-2 mb-4">
              <div class="flex justify-between text-base font-bold text-slate-900">
                <span>Total:</span>
                <span>${totalAmount.toFixed(2)}</span>
              </div>
            </div>

            <!-- MÉTODO DE PAGO -->
            <div class="space-y-3 pt-3 border-t border-slate-100">
              <span class="block text-xs font-semibold text-slate-700">Método de Pago:</span>
              <div class="grid grid-cols-2 gap-2">
                <button
                  type="button"
                  onclick={() => paymentMethod = 'CASH'}
                  class="py-2 rounded-lg text-sm font-semibold border-2 transition {paymentMethod === 'CASH' ? 'border-black bg-neutral-100 text-black' : 'border-slate-200 text-slate-600'}"
                >
                  💵 Efectivo
                </button>
                <button
                  type="button"
                  onclick={() => paymentMethod = 'CARD'}
                  class="py-2 rounded-lg text-sm font-semibold border-2 transition {paymentMethod === 'CARD' ? 'border-black bg-neutral-100 text-black' : 'border-slate-200 text-slate-600'}"
                >
                  💳 Tarjeta
                </button>
              </div>

              {#if paymentMethod === 'CASH'}
                <div class="space-y-2 pt-2">
                  <label class="block text-xs font-semibold text-slate-700">Efectivo Recibido:</label>
                  <input
                    type="number"
                    step="0.50"
                    bind:value={cashGiven}
                    placeholder="0.00"
                    class="w-full px-3 py-2 border rounded-lg text-sm font-bold text-slate-800"
                  />
                  <div class="flex justify-between text-xs pt-1">
                    <span class="text-slate-500 font-semibold">Cambio:</span>
                    <span class="font-bold text-emerald-600 text-base">${changeAmount}</span>
                  </div>
                </div>
              {/if}

              <button
                onclick={handleCheckout}
                disabled={$cart.length === 0}
                class="w-full mt-4 bg-emerald-600 hover:bg-emerald-700 text-white font-bold py-3 px-4 rounded-xl shadow-sm transition disabled:opacity-50"
              >
                ✅ Cobrar Orden
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  {/if}
</div>

<!-- MODAL: CIERRE DE TURNO -->
{#if showCloseModal && $currentShift}
  <div class="fixed inset-0 bg-slate-900/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
    <div class="bg-white rounded-2xl shadow-2xl max-w-md w-full p-6">
      <h3 class="text-lg font-bold text-slate-900 mb-1">Cierre de Turno y Arqueo Físico</h3>
      <p class="text-xs text-slate-500 mb-4">Ingresa el dinero físico contado en el cajón.</p>

      <form onsubmit={handleCloseShift} class="space-y-4">
        <div class="bg-slate-50 p-3 rounded-xl border border-slate-200 text-xs flex justify-between">
          <span class="text-slate-600">Efectivo esperado por el sistema:</span>
          <span class="font-bold text-slate-900">${parseFloat($currentShift.expected_cash).toFixed(2)}</span>
        </div>

        <div>
          <label class="block text-xs font-semibold text-slate-700 mb-1">Efectivo Físico Contado:</label>
          <input
            type="number"
            step="0.50"
            bind:value={closeActualCash}
            required
            placeholder="0.00"
            class="w-full px-3 py-2 rounded-lg border border-slate-300 text-base font-bold text-slate-800"
          />
        </div>

        <div>
          <label class="block text-xs font-semibold text-slate-700 mb-1">Notas de Cierre:</label>
          <input
            type="text"
            bind:value={closeNotes}
            placeholder="Sin observaciones"
            class="w-full px-3 py-2 rounded-lg border border-slate-300 text-sm"
          />
        </div>

        <div class="flex space-x-3 pt-2">
          <button
            type="button"
            onclick={() => showCloseModal = false}
            class="w-1/2 py-2.5 rounded-xl border border-slate-300 text-slate-700 text-sm font-semibold hover:bg-slate-50"
          >
            Cancelar
          </button>
          <button
            type="submit"
            class="w-1/2 py-2.5 rounded-xl bg-rose-600 hover:bg-rose-700 text-white text-sm font-semibold shadow"
          >
            Confirmar Cierre
          </button>
        </div>
      </form>
    </div>
  </div>
{/if}
