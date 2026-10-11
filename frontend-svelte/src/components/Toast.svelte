<script>
  import { toast } from '../lib/stores.js';
</script>

{#if $toast.show}
  <div
    class="fixed bottom-6 right-6 z-50 max-w-md px-5 py-4 rounded-xl shadow-2xl text-white font-medium text-sm transition transform flex items-center space-x-3 {$toast.isError ? 'bg-rose-600' : 'bg-emerald-600'}"
  >
    <span>{$toast.isError ? '⚠️' : '✅'}</span>
    <span>{$toast.message}</span>
  </div>
{/if}
