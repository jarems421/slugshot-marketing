import React, {useCallback, useEffect, useMemo, useState} from 'react';
import {
	AbsoluteFill,
	Audio,
	Loop,
	OffthreadVideo,
	Sequence,
	continueRender,
	delayRender,
	interpolate,
	staticFile,
	useCurrentFrame,
	useVideoConfig,
} from 'remotion';
import {Caption, createTikTokStyleCaptions, parseSrt} from '@remotion/captions';

export type VerticalProps = {
	clip: string; // path under public/
	clipLengthSeconds: number | null; // set when the clip is shorter than clipSeconds, so it loops
	narration: string | null; // path under public/, or null to use only the clip's audio
	captions: string | null; // .srt or Caption[] .words.json under public/ (written by scripts/caption.py)
	clipVolume: number;
	fit: 'crop' | 'blur';
	hook: string;
	hookSeconds: number;
	clipSeconds: number;
	endCard: boolean;
	endCardTitle: string;
	endCardSubtitle: string;
	endCardSeconds: number;
	accent: string; // hook box and highlighted word
	captionTop: number; // 0-1, top of the caption block
	label: string; // persistent corner tag, e.g. "Fictional story" or "AI-generated scene"; '' for none
};

const FONT = '"Arial Black", "Segoe UI Black", Impact, sans-serif';
const INK = '#16161a';

// Platform buttons cover roughly the bottom quarter and the top tenth, so text sits between.
const outline = (px: number) =>
	`-${px}px -${px}px 0 ${INK}, ${px}px -${px}px 0 ${INK}, -${px}px ${px}px 0 ${INK}, ${px}px ${px}px 0 ${INK}, 0 ${px * 2}px ${px * 3}px rgba(0,0,0,.5)`;

const Clip: React.FC<Pick<VerticalProps, 'clip' | 'clipVolume' | 'fit'>> = ({clip, clipVolume, fit}) => {
	const src = staticFile(clip);
	if (fit === 'crop') {
		return <OffthreadVideo src={src} volume={clipVolume} style={{width: '100%', height: '100%', objectFit: 'cover'}} />;
	}
	return (
		<AbsoluteFill>
			<OffthreadVideo
				src={src}
				muted
				style={{width: '100%', height: '100%', objectFit: 'cover', filter: 'blur(40px) brightness(.55)', transform: 'scale(1.15)'}}
			/>
			<AbsoluteFill style={{justifyContent: 'center'}}>
				<OffthreadVideo src={src} volume={clipVolume} style={{width: '100%', objectFit: 'contain'}} />
			</AbsoluteFill>
		</AbsoluteFill>
	);
};

const Captions: React.FC<{file: string; accent: string; top: number}> = ({file, accent, top}) => {
	const frame = useCurrentFrame();
	const {fps} = useVideoConfig();
	const [captions, setCaptions] = useState<Caption[] | null>(null);
	const [handle] = useState(() => delayRender('Loading captions'));

	// A hand-checked .srt is the normal source (one file to correct); .words.json gives per-word highlight.
	const load = useCallback(async () => {
		const res = await fetch(staticFile(file));
		setCaptions(file.endsWith('.srt') ? parseSrt({input: await res.text()}).captions : ((await res.json()) as Caption[]));
		continueRender(handle);
	}, [file, handle]);

	useEffect(() => {
		load();
	}, [load]);

	const wordLevel = !file.endsWith('.srt');
	const pages = useMemo(() => {
		if (!captions) return [];
		if (wordLevel) return createTikTokStyleCaptions({captions, combineTokensWithinMilliseconds: 900}).pages;
		return captions.map((c) => ({startMs: c.startMs, tokens: [{text: c.text, fromMs: c.startMs, toMs: c.endMs}]}));
	}, [captions, wordLevel]);

	const ms = (frame / fps) * 1000;
	const page = pages.find((p, i) => {
		const end = pages[i + 1]?.startMs ?? p.tokens[p.tokens.length - 1].toMs + 400;
		return ms >= p.startMs && ms < end;
	});
	if (!page) return null;

	return (
		<AbsoluteFill style={{top: `${top * 100}%`, height: 'auto', alignItems: 'center', padding: '0 70px'}}>
			<div style={{fontFamily: FONT, fontSize: 84, lineHeight: 1.1, textAlign: 'center', textShadow: outline(5), whiteSpace: 'pre-wrap'}}>
				{page.tokens.map((t) => (
					<span key={t.fromMs} style={{color: wordLevel && ms >= t.fromMs && ms < t.toMs ? accent : '#ffffff'}}>
						{t.text}
					</span>
				))}
			</div>
		</AbsoluteFill>
	);
};

const Label: React.FC<{text: string}> = ({text}) => (
	<AbsoluteFill style={{top: 150, left: 40, width: 'auto', height: 'auto'}}>
		<div style={{fontFamily: FONT, fontSize: 34, color: '#fff', background: 'rgba(22,22,26,.72)', padding: '8px 18px', borderRadius: 10}}>
			{text}
		</div>
	</AbsoluteFill>
);

const Hook: React.FC<{text: string; seconds: number; accent: string}> = ({text, seconds, accent}) => {
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

const EndCard: React.FC<{title: string; subtitle: string}> = ({title, subtitle}) => {
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

export const Vertical: React.FC<VerticalProps> = (p) => {
	const {fps} = useVideoConfig();
	const clipFrames = Math.ceil(p.clipSeconds * fps);
	return (
		<AbsoluteFill style={{background: '#000'}}>
			<Sequence durationInFrames={clipFrames}>
				{p.clipLengthSeconds && p.clipLengthSeconds < p.clipSeconds ? (
					<Loop durationInFrames={Math.floor(p.clipLengthSeconds * fps)}>
						<Clip clip={p.clip} clipVolume={p.clipVolume} fit={p.fit} />
					</Loop>
				) : (
					<Clip clip={p.clip} clipVolume={p.clipVolume} fit={p.fit} />
				)}
				{p.narration ? <Audio src={staticFile(p.narration)} /> : null}
				{p.captions ? <Captions file={p.captions} accent={p.accent} top={p.captionTop} /> : null}
				{p.hook ? <Hook text={p.hook} seconds={p.hookSeconds} accent={p.accent} /> : null}
				{p.label ? <Label text={p.label} /> : null}
			</Sequence>
			{p.endCard ? (
				<Sequence from={clipFrames} durationInFrames={Math.ceil(p.endCardSeconds * fps)}>
					<EndCard title={p.endCardTitle} subtitle={p.endCardSubtitle} />
				</Sequence>
			) : null}
		</AbsoluteFill>
	);
};
