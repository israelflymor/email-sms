const http = require('http');
const fs = require('fs');
const path = require('path');

const PORT = process.env.PORT || 5173;
const root = __dirname;
const API_TARGET = process.env.API_TARGET || 'http://localhost:8000';

const mime = {
  '.html': 'text/html; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.js': 'application/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8'
};

function proxyApi(req, res) {
  const target = new URL(API_TARGET);
  const upstreamPath = req.url.replace(/^\/api/, '') || '/';

  const options = {
    hostname: target.hostname,
    port: target.port || (target.protocol === 'https:' ? 443 : 80),
    path: upstreamPath,
    method: req.method,
    headers: { ...req.headers, host: target.host },
  };

  const proxyReq = http.request(options, (proxyRes) => {
    res.writeHead(proxyRes.statusCode || 502, proxyRes.headers);
    proxyRes.pipe(res, { end: true });
  });

  proxyReq.on('error', (err) => {
    res.writeHead(502, { 'Content-Type': 'application/json; charset=utf-8' });
    res.end(JSON.stringify({
      error: 'api_proxy_failed',
      message: err.message,
      target: API_TARGET,
      hint: 'Start the backend API on port 8000 or set API_TARGET to the correct backend URL.'
    }));
  });

  req.pipe(proxyReq, { end: true });
}

function serveStatic(req, res) {
  let reqPath = req.url.split('?')[0];
  if (reqPath === '/') reqPath = '/index.html';
  const filePath = path.join(root, reqPath);

  if (!filePath.startsWith(root)) {
    res.writeHead(403, { 'Content-Type': 'text/plain; charset=utf-8' });
    res.end('Forbidden');
    return;
  }

  fs.readFile(filePath, (err, data) => {
    if (err) {
      res.writeHead(404, { 'Content-Type': 'text/plain; charset=utf-8' });
      res.end('Not found');
      return;
    }
    const ext = path.extname(filePath).toLowerCase();
    res.writeHead(200, { 'Content-Type': mime[ext] || 'application/octet-stream' });
    res.end(data);
  });
}

http.createServer((req, res) => {
  if (req.url.startsWith('/api/')) {
    return proxyApi(req, res);
  }
  return serveStatic(req, res);
}).listen(PORT, () => {
  console.log(`Admin UI running at http://localhost:${PORT}`);
  console.log(`Proxying /api/* to ${API_TARGET}`);
});
