import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';
import fs from 'fs';

export default defineConfig({
  base: './',
  plugins: [
    react(),
    {
      name: 'serve-parent-data',
      configureServer(server) {
        // Serve parent /data directory for ultra-fast JSON sharding
        server.middlewares.use((req, res, next) => {
          if (req.url && req.url.startsWith('/data/')) {
            const relativePath = req.url.split('?')[0];
            const publicFilePath = path.resolve(__dirname, 'public', relativePath.slice(1));
            const parentFilePath = path.resolve(__dirname, '..', relativePath.slice(1));
            const targetPath = fs.existsSync(publicFilePath) ? publicFilePath : (fs.existsSync(parentFilePath) ? parentFilePath : null);
            if (targetPath) {
              res.setHeader('Content-Type', 'application/json');
              res.setHeader('Access-Control-Allow-Origin', '*');
              fs.createReadStream(targetPath).pipe(res);
              return;
            }
          }
          if (req.url && (
            req.url.startsWith('/skills_map.json') || 
            req.url.startsWith('/ultimate_leetcode_master.json') || 
            req.url.startsWith('/all_leetcode_problems_and_topics.json') ||
            req.url.startsWith('/scraped_image_walkin_jobs.json')
          )) {
            const relativePath = req.url.split('?')[0];
            const parentFilePath = path.resolve(__dirname, '..', relativePath.slice(1));
            if (fs.existsSync(parentFilePath)) {
              res.setHeader('Content-Type', 'application/json');
              res.setHeader('Access-Control-Allow-Origin', '*');
              fs.createReadStream(parentFilePath).pipe(res);
              return;
            }
          }
          next();
        });
      }
    }
  ],
  server: {
    port: 5173,
    host: true
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src')
    }
  }
});
