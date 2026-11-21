// Print the deployed contract address for a deploy tx hash.
// The address is the deploy transaction's to_address (it is NOT in the eth receipt).
// Usage: node contract_address.mjs <deployTxHash>
import { createClient } from 'genlayer-js';
import { studioDevnet } from 'genlayer-js/chains';
import { http } from 'viem';
const client = createClient({ chain: studioDevnet, transport: http(studioDevnet.rpcUrls.default.http[0]) });
const tx = await client.getTransaction({ hash: process.argv[2] });
console.log(tx.to_address);
