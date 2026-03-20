// Persistent runner for OpenClaw Evo Hub
import { EvoHub } from './dist/hub.js';
import { DEFAULT_CONFIG } from './dist/constants.js';
import { startServer } from './dist/server.js';
import { createWriteStream } from 'node:fs';

const LOG = createWriteStream('./hub-output.log', { flags: 'a' });
const log = (...args) => LOG.write(args.join(' ') + '\n');

const PORT = parseInt(process.env.EVO_DASHBOARD_PORT ?? '5175');
const hub = new EvoHub(DEFAULT_CONFIG);

process.on('unhandledRejection', (err) => {
  log('[FATAL] Unhandled rejection:', String(err));
  process.exit(1);
});

process.on('exit', () => log('[EXIT] process exiting'));

try {
  log('[START] Calling hub.start()...');
  await hub.start();
  log('[START] hub.start() done, calling startServer()...');
  const server = startServer(hub, PORT);
  log(`[OK] Evo Hub + API running on port ${PORT}`);
  log(`[OK] Dashboard: http://localhost:${PORT}`);
  // Keep alive
  await new Promise(() => {});
} catch (err) {
  log('[ERROR] Failed to start hub:', String(err));
  process.exit(1);
}
