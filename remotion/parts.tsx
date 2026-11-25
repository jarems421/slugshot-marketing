import React, {useCallback, useEffect, useMemo, useState} from 'react';
import {
	AbsoluteFill,
	Img,
	OffthreadVideo,
	continueRender,
	delayRender,
	interpolate,
	staticFile,
	useCurrentFrame,
	useVideoConfig,
} from 'remotion';
import {Caption, createTikTokStyleCaptions, parseSrt} from '@remotion/captions';

// Kalam Bold: the game's one font (owner, 2026-11-22). It draws about 70% the size of Arial Black at the
// same font-size, so sizes below are scaled up. Loaded from public/fonts (staged from assets/brand).
export const FONT = '"Kalam", "Arial Black", "Segoe UI Black", sans-serif';
export const INK = '#18161c'; // charcoal, not pure black (style guide: ink outlines)

const fontHandle = typeof window === 'undefined' ? null : delayRender('Loading Kalam');
if (typeof window !== 'undefined') {
	new FontFace('Kalam', `url(${staticFile('fonts/Kalam-Bold.ttf')}) format('truetype')`, {weight: '700'})
		.load()
		.then((f) => {
			document.fonts.add(f);
			if (fontHandle !== null) continueRender(fontHandle);
		})
		.catch(() => {
			if (fontHandle !== null) continueRender(fontHandle); // falls back to Arial Black
		});
}

// Platform buttons cover roughly the bottom quarter and the top tenth, so text sits between.
export const outline = (px: number) =>
	`-${px}px -${px}px 0 ${INK}, ${px}px -${px}px 0 ${INK}, -${px}px ${px}px 0 ${INK}, ${px}px ${px}px 0 ${INK}, 0 ${px * 2}px ${px * 3}px rgba(0,0,0,.5)`;

const norm = (s: string) => s.toLowerCase().replace(/[^a-z0-9]/g, '');

export type Fit = 'crop' | 'blur' | 'contain';

/** A video or still image filling the 9:16 frame. `zoom` is the scale reached by the end (slow push-in);
 * `punchAt` lists seconds where the shot snaps 12% closer (a motivated punch-in that holds). */
export const Media: React.FC<{
	src: string;
	kind: 'video' | 'image';
	fit: Fit;
	volume?: number;
	trimStartSeconds?: number;
	durationFrames: number;
	zoom?: number;
	punchAt?: number[];
}> = ({src, kind, fit, volume = 0, trimStartSeconds = 0, durationFrames, zoom = 1, punchAt = []}) => {
	const frame = useCurrentFrame();
	const {fps} = useVideoConfig();
	const push = interpolate(frame, [0, durationFrames], [1, zoom], {extrapolateRight: 'clamp'});
	const punch = punchAt.reduce(
		(s, t) => s * interpolate(frame, [t * fps, t * fps + 3], [1, 1.12], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}),
		1,
	);
	const url = staticFile(src);
	const layer = (style: React.CSSProperties, muted: boolean) =>
		kind === 'image' ? (
			<Img src={url} style={style} />
		) : (
			<OffthreadVideo src={url} muted={muted} volume={volume} trimBefore={Math.round(trimStartSeconds * fps)} style={style} />
		);
	const scale = {transform: `scale(${push * punch})`};
	if (fit === 'crop') {
		return <AbsoluteFill style={scale}>{layer({width: '100%', height: '100%', objectFit: 'cover'}, false)}</AbsoluteFill>;
	}
	return (
		<AbsoluteFill style={{background: '#000'}}>
			{fit === 'blur'
				? layer({width: '100%', height: '100%', objectFit: 'cover', filter: 'blur(40px) brightness(.55)', transform: 'scale(1.15)'}, true)
				: null}
			<AbsoluteFill style={{justifyContent: 'center', ...scale}}>{layer({width: '100%', objectFit: 'contain'}, false)}</AbsoluteFill>
		</AbsoluteFill>
	);
};

/** Captions from a hand-checked .srt (phrases) or .words.json (word-by-word highlight).
 * Words listed in `emphasis` always show in the accent colour, a little larger. */
export const Captions: React.FC<{file: string; accent: string; top: number; emphasis?: string[]; hide?: [number, number][]}> = ({
	file,
	accent,
	top,
	emphasis = [],
	hide = [],
}) => {
	const frame = useCurrentFrame();
	const {fps} = useVideoConfig();
	const [captions, setCaptions] = useState<Caption[] | null>(null);
	const [handle] = useState(() => delayRender('Loading captions'));

	const load = useCallback(async () => {
		const res = await fetch(staticFile(file));
		setCaptions(file.endsWith('.srt') ? parseSrt({input: await res.text()}).captions : ((await res.json()) as Caption[]));
		continueRender(handle);
	}, [file, handle]);

	useEffect(() => {
		load();
	}, [load]);

	type Token = {text: string; fromMs: number; toMs: number; color?: string};
	type Dialogue = Caption & {speaker?: string; color?: string; lineStart?: boolean};
	// Dialogue words (scripts/dialogue.py) carry a speaker: pages never mix speakers, break at punctuation or
	// four words, take the speaker's colour, and don't bounce word by word (a deadpan line stays deadpan).
	const dialogue = !!captions && captions.length > 0 && 'speaker' in (captions[0] as Dialogue);
	const wordLevel = !file.endsWith('.srt') && !dialogue;
	const pages = useMemo((): {startMs: number; tokens: Token[]}[] => {
		if (!captions) return [];
		if (dialogue) {
			// One page per spoken line when it is short (a punchline stays whole); longer lines split into
			// balanced pages, preferring breaks after punctuation.
			const out: {startMs: number; tokens: Token[]}[] = [];
			const lines: Token[][] = [];
			let speaker: string | undefined;
			for (const c of captions as Dialogue[]) {
				if (c.speaker !== speaker || c.lineStart || !lines.length) lines.push([]);
				speaker = c.speaker;
				lines[lines.length - 1].push({text: c.text, fromMs: c.startMs, toMs: c.endMs, color: c.color});
			}
			for (const line of lines) {
				const pagesNeeded = line.length <= 6 ? 1 : Math.ceil(line.length / 5);
				const size = Math.ceil(line.length / pagesNeeded);
				let cur: Token[] = [];
				line.forEach((t, i) => {
					cur.push(t);
					const left = line.length - i - 1;
					const punct = /[.,!?;:…]$/.test(t.text.trim());
					if (left > 0 && cur.length >= size - (punct ? 1 : 0) && left >= 2) {
						out.push({startMs: cur[0].fromMs, tokens: cur});
						cur = [];
					}
				});
				if (cur.length) out.push({startMs: cur[0].fromMs, tokens: cur});
			}
			return out;
		}
		if (wordLevel) return createTikTokStyleCaptions({captions, combineTokensWithinMilliseconds: 900}).pages;
		// Phrase captions: split into words so emphasis still works.
		return captions.map((c) => ({
			startMs: c.startMs,
			tokens: c.text.split(/(?=\s)/).map((w) => ({text: w, fromMs: c.startMs, toMs: c.endMs})),
		}));
	}, [captions, wordLevel, dialogue]);
	const strong = useMemo(() => new Set(emphasis.map(norm)), [emphasis]);

	const ms = (frame / fps) * 1000;
	// A page stays up until the next one starts, but a dialogue page clears 350 ms after its last word so held
	// silences read as silences.
	const page = pages.find((p, i) => {
		const last = p.tokens[p.tokens.length - 1].toMs;
		const next = pages[i + 1]?.startMs ?? last + 400;
		const end = dialogue ? Math.min(next, last + 350) : next;
		return ms >= p.startMs && ms < end;
	});
	if (!page || hide.some(([a, b]) => frame >= a && frame < b)) return null;
	const pop = interpolate(ms - page.startMs, [0, 90], [0.94, 1], {extrapolateRight: 'clamp'});

	return (
		<AbsoluteFill style={{top: `${top * 100}%`, height: 'auto', alignItems: 'center', padding: '0 70px'}}>
			<div
				style={{
					fontFamily: FONT,
					fontWeight: 700,
					fontSize: 108,
					lineHeight: 1.0,
					textAlign: 'center',
					textShadow: outline(6),
					whiteSpace: 'pre-wrap',
					transform: `scale(${pop})`,
				}}
			>
				{page.tokens.map((t, i) => {
					const key = strong.has(norm(t.text));
					const active = wordLevel && ms >= t.fromMs && ms < t.toMs;
					return (
						<span
							key={`${t.fromMs}-${i}`}
							style={{color: key || active ? accent : (t.color ?? '#ffffff'), fontSize: key ? '1.15em' : undefined}}
						>
							{i === 0 ? t.text.trimStart() : t.text}
						</span>
					);
				})}
			</div>
		</AbsoluteFill>
	);
};

export const Label: React.FC<{text: string; top?: number}> = ({text, top = 230}) => (
	<AbsoluteFill style={{top, left: 40, width: 'auto', height: 'auto'}}>
		<div style={{fontFamily: FONT, fontWeight: 700, fontSize: 44, color: '#fff', background: 'rgba(22,22,26,.72)', padding: '8px 18px', borderRadius: 10}}>
			{text}
		</div>
	</AbsoluteFill>
);

export const Hook: React.FC<{text: string; seconds: number; accent: string}> = ({text, seconds, accent}) => {
	const frame = useCurrentFrame();
	const {fps} = useVideoConfig();
	const end = seconds * fps;
	const opacity = interpolate(frame, [0, 4, end - 6, end], [0, 1, 1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
	const scale = interpolate(frame, [0, 6], [0.9, 1], {extrapolateRight: 'clamp'});
	return (
		<AbsoluteFill style={{top: '13%', height: 'auto', alignItems: 'center', padding: '0 60px', opacity}}>
			<div
				style={{
					fontFamily: FONT,
					fontSize: 72,
					color: INK,
					background: accent,
					border: `6px solid ${INK}`,
					borderRadius: 18,
					padding: '18px 30px',
					textAlign: 'center',
					transform: `scale(${scale}) rotate(-1.5deg)`,
				}}
			>
				{text}
			</div>
		</AbsoluteFill>
	);
};

/** Full-frame text card, e.g. a title beat between scenes. */
export const TextCard: React.FC<{text: string; accent: string}> = ({text, accent}) => {
	const frame = useCurrentFrame();
	const pop = interpolate(frame, [0, 6], [0.85, 1], {extrapolateRight: 'clamp'});
	return (
		<AbsoluteFill style={{background: '#1d1a24', justifyContent: 'center', alignItems: 'center', padding: '0 80px'}}>
			<div style={{fontFamily: FONT, fontSize: 96, color: accent, textShadow: outline(6), textAlign: 'center', lineHeight: 1.1, transform: `scale(${pop})`}}>
				{text}
			</div>
		</AbsoluteFill>
	);
};

export const EndCard: React.FC<{title: string; subtitle: string}> = ({title, subtitle}) => {
	const frame = useCurrentFrame();
	const pop = interpolate(frame, [0, 8], [0.7, 1], {extrapolateRight: 'clamp'});
	return (
		<AbsoluteFill style={{background: '#1d1a24', justifyContent: 'center', alignItems: 'center'}}>
			<div
				style={{
					fontFamily: FONT,
					fontSize: title.length > 9 ? 120 : 150,
					color: '#ffd23f',
					textShadow: outline(8),
					textAlign: 'center',
					padding: '0 60px',
					lineHeight: 1.05,
					transform: `scale(${pop})`,
				}}
			>
				{title}
			</div>
			<div style={{fontFamily: FONT, fontSize: 52, color: '#ffffff', marginTop: 30, textAlign: 'center', padding: '0 80px'}}>{subtitle}</div>
		</AbsoluteFill>
	);
};
