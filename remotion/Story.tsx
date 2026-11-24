import React from 'react';
import {AbsoluteFill, Audio, Sequence, interpolate, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {Captions, EndCard, Fit, Hook, Label, Media, TextCard} from './parts';

export type Scene = {
	kind: 'video' | 'image' | 'card';
	src?: string; // under public/ (video or image)
	text?: string; // card text
	seconds: number; // time on screen
	trimStartSeconds?: number; // video in-point
	fit?: Fit;
	volume?: number; // the clip's own audio
	zoom?: number; // scale reached by the end of the scene (1 = still)
	punchAt?: number[]; // seconds into the scene for a punch-in
	transition?: 'cut' | 'fade'; // how this scene starts
	label?: string; // tag for this scene only, e.g. "AI-generated scene"
	captions?: boolean; // show captions during this scene (default: yes, except on text cards)
};

export type StoryProps = {
	scenes: Scene[];
	narration: string | null; // full mix (voice + ducked music + SFX) from scripts/assemble.py
	captions: string | null;
	emphasis: string[];
	hook: string;
	hookSeconds: number;
	accent: string;
	captionTop: number;
	label: string; // tag for the whole video
	endCard: boolean;
	endCardTitle: string;
	endCardSubtitle: string;
	endCardSeconds: number;
};

const FadeIn: React.FC<{children: React.ReactNode; on: boolean}> = ({children, on}) => {
	const frame = useCurrentFrame();
	const opacity = on ? interpolate(frame, [0, 8], [0, 1], {extrapolateRight: 'clamp'}) : 1;
	return <AbsoluteFill style={{opacity, background: '#000'}}>{children}</AbsoluteFill>;
};

export const storyFrames = (p: StoryProps, fps: number) =>
	p.scenes.reduce((n, s) => n + Math.round(s.seconds * fps), 0) + (p.endCard ? Math.round(p.endCardSeconds * fps) : 0);

export const Story: React.FC<StoryProps> = (p) => {
	const {fps} = useVideoConfig();
	let from = 0;
	const body = p.scenes.reduce((n, s) => n + Math.round(s.seconds * fps), 0);
	// Cards already show their words, so captions would say the same thing twice.
	const hide: [number, number][] = [];
	p.scenes.reduce((start, s) => {
		const end = start + Math.round(s.seconds * fps);
		if (s.captions === false || (s.kind === 'card' && s.captions !== true)) hide.push([start, end]);
		return end;
	}, 0);
	return (
		<AbsoluteFill style={{background: '#000'}}>
			{p.scenes.map((s, i) => {
				const frames = Math.round(s.seconds * fps);
				const start = from;
				from += frames;
				return (
					<Sequence key={i} from={start} durationInFrames={frames}>
						<FadeIn on={s.transition === 'fade'}>
							{s.kind === 'card' ? (
								<TextCard text={s.text ?? ''} accent={p.accent} />
							) : (
								<Media
									src={s.src!}
									kind={s.kind}
									fit={s.fit ?? 'crop'}
									volume={s.volume ?? 0}
									trimStartSeconds={s.trimStartSeconds}
									durationFrames={frames}
									zoom={s.zoom}
									punchAt={s.punchAt}
								/>
							)}
						</FadeIn>
						{s.label ? <Label text={s.label} top={p.label ? 215 : 150} /> : null}
					</Sequence>
				);
			})}
			<Sequence durationInFrames={body}>
				{p.narration ? <Audio src={staticFile(p.narration)} /> : null}
				{p.captions ? <Captions file={p.captions} accent={p.accent} top={p.captionTop} emphasis={p.emphasis} hide={hide} /> : null}
				{p.hook ? <Hook text={p.hook} seconds={p.hookSeconds} accent={p.accent} /> : null}
				{p.label ? <Label text={p.label} /> : null}
			</Sequence>
			{p.endCard ? (
				<Sequence from={body} durationInFrames={Math.round(p.endCardSeconds * fps)}>
					<EndCard title={p.endCardTitle} subtitle={p.endCardSubtitle} />
				</Sequence>
			) : null}
		</AbsoluteFill>
	);
};
