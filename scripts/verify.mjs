// Read DelegateCourt state back from Studio Next.
// Usage: node verify.mjs <contractAddress> [dealId] [mandateId]
// Defaults: deal-001 / mandate-001.
import { createClient } from 'genlayer-js';
import { studioDevnet } from 'genlayer-js/chains';
import { http } from 'viem';

const addr = process.argv[2];
const dealId = process.argv[3] || 'deal-001';
const mandateId = process.argv[4] || 'mandate-001';
if (!addr) { console.error('usage: node verify.mjs <contract> [dealId] [mandateId]'); process.exit(1); }
const client = createClient({ chain: studioDevnet, transport: http(studioDevnet.rpcUrls.default.http[0]) });

for (const [fn, args] of [
  ['get_name', []],
  ['get_status', [dealId]],
  ['get_deal', [dealId]],
  ['get_mandate', [mandateId]],
  ['is_revoked', [mandateId]],
  ['get_decision', [dealId]],
]) {
  try {
    const r = await client.readContract({ address: addr, functionName: fn, args });
    console.log(`${fn}(${args.join(', ')}) =>`, JSON.stringify(r));
  } catch (e) {
    console.log(`${fn}(${args.join(', ')}) ERROR:`, e.message);
  }
}
