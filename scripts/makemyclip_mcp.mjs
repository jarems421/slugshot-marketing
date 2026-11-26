import { fileURLToPath } from 'node:url';

const media = new URL('../media/', import.meta.url);
const cli = new URL('../node_modules/@makemyclip/editor/dist/cli.js', import.meta.url);
process.env.MAKEMYCLIP_WORKSPACE = fileURLToPath(media);
process.env.MAKEMYCLIP_FFMPEG_PATH ||= 'ffmpeg';
process.argv.splice(1, 1, fileURLToPath(cli), 'mcp');
await import(cli.href);
