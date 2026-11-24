import React from 'react';
import {AbsoluteFill, Audio, Loop, Sequence, staticFile, useVideoConfig} from 'remotion';
import {Captions, EndCard, Hook, Label, Media} from './parts';

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
	emphasis?: string[]; // words always shown in the accent colour
};

export const Vertical: React.FC<VerticalProps> = (p) => {
	const {fps} = useVideoConfig();
	const clipFrames = Math.ceil(p.clipSeconds * fps);
	const loopFrames = p.clipLengthSeconds && p.clipLengthSeconds < p.clipSeconds ? Math.floor(p.clipLengthSeconds * fps) : 0;
	const media = <Media src={p.clip} kind="video" fit={p.fit} volume={p.clipVolume} durationFrames={loopFrames || clipFrames} />;
	return (
		<AbsoluteFill style={{background: '#000'}}>
			<Sequence durationInFrames={clipFrames}>
				{loopFrames ? <Loop durationInFrames={loopFrames}>{media}</Loop> : media}
				{p.narration ? <Audio src={staticFile(p.narration)} /> : null}
				{p.captions ? <Captions file={p.captions} accent={p.accent} top={p.captionTop} emphasis={p.emphasis} /> : null}
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
