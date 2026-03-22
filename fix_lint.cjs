const fs = require('fs');
const lines = fs.readFileSync('src/builder/templateLibrary.ts', 'utf8').split('\n');
[158,159,160,167,168,169].forEach(n => {
  const l = lines[n];
  console.log(`${n+1}: ${l}`);
  const bytes = [...l].map(c => c.charCodeAt(0) === 92 ? '\\' : String(c.charCodeAt(0)));
  console.log('   bytes:', bytes.join(' '));
});
