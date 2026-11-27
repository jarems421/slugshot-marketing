import { existsSync, readdirSync } from 'node:fs';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';

const media = new URL('../media/', import.meta.url);
const cli = new URL('../node_modules/@makemyclip/editor/dist/cli.js', import.meta.url);

// FFmpeg: the environment's choice, else a WinGet install (not always on PATH for this process), else PATH.
function wingetFfmpeg() {
  const packages = join(process.env.LOCALAPPDATA || '', 'Microsoft', 'WinGet', 'Packages');
  if (!existsSync(packages)) return null;
  for (const pkg of readdirSync(packages).filter((name) => name.startsWith('Gyan.FFmpeg'))) {
    for (const build of readdirSync(join(packages, pkg))) {
      const exe = join(packages, pkg, build, 'bin', 'ffmpeg.exe');
      if (existsSync(exe)) return exe;
    }
  }
  return null;
}

process.env.MAKEMYCLIP_WORKSPACE = fileURLToPath(media);
process.env.MAKEMYCLIP_FFMPEG_PATH ||= wingetFfmpeg() || 'ffmpeg';
process.argv.splice(1, 1, fileURLToPath(cli), 'mcp');
await import(cli.href);
