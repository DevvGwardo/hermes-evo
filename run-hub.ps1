$env:EVO_DASHBOARD_PORT = "5175"
$env:NODE_ENV = "production"
$hubScript = @"
import { EvoHub } from './dist/hub.js';
import { DEFAULT_CONFIG } from './dist/constants.js';
import { startServer } from './dist/server.js';

const PORT = parseInt(process.env.EVO_DASHBOARD_PORT ?? '5175');
const hub = new EvoHub(DEFAULT_CONFIG);
await hub.start();
const server = startServer(hub, PORT);
console.log(`Evo Hub running on port ${PORT}`);
process.stdin.resume();
"@

$tmp = Join-Path $env:TEMP "evo-hub-runner.mjs"
[System.IO.File]::WriteAllText($tmp, $hubScript, [System.Text.UTF8Encoding]::new($true))
Set-Location "C:\Users\torre\.openclaw\workspace\openclaw-evo"
node $tmp
