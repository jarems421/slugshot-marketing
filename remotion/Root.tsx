import React from 'react';
import {Composition} from 'remotion';
import {Story, StoryProps, storyFrames} from './Story';
import {Vertical, VerticalProps} from './Vertical';

const FPS = 30;

// Defaults point at the sample files staged in public/sample/ (git-ignored), for Remotion Studio.
const verticalDefaults: VerticalProps = {
	clip: 'sample/clip.mp4',
	clipLengthSeconds: null,
	narration: 'sample/narration.wav',
	captions: 'sample/captions.srt',
	clipVolume: 0,
	fit: 'blur',
	hook: 'TEST RENDER - not gameplay',
	hookSeconds: 2.5,
	clipSeconds: 10,
	endCard: true,
	endCardTitle: 'SLUGSHOT',
	endCardSubtitle: 'A Roblox creature-combat game',
	endCardSeconds: 2,
	accent: '#ffd23f',
	captionTop: 0.69,
	label: '',
	emphasis: [],
};

const storyDefaults: StoryProps = {
	scenes: [
		{kind: 'card', text: 'Scene 1', seconds: 1.5},
		{kind: 'video', src: 'sample/clip.mp4', seconds: 3, fit: 'blur', zoom: 1.08},
	],
	narration: null,
	captions: null,
	emphasis: [],
	hook: '',
	hookSeconds: 2.5,
	accent: '#ffd23f',
	captionTop: 0.69,
	label: 'TEST - not gameplay',
	endCard: true,
	endCardTitle: 'SLUGSHOT',
	endCardSubtitle: 'A Roblox creature-combat game',
	endCardSeconds: 2,
};

export const RemotionRoot: React.FC = () => (
	<>
		<Composition
			id="Vertical"
			component={Vertical}
			width={1080}
			height={1920}
			fps={FPS}
			durationInFrames={FPS * 12}
			defaultProps={verticalDefaults}
			calculateMetadata={({props}) => ({
				durationInFrames: Math.ceil(FPS * (props.clipSeconds + (props.endCard ? props.endCardSeconds : 0))),
			})}
		/>
		<Composition
			id="Story"
			component={Story}
			width={1080}
			height={1920}
			fps={FPS}
			durationInFrames={FPS * 10}
			defaultProps={storyDefaults}
			calculateMetadata={({props}) => ({durationInFrames: storyFrames(props, FPS)})}
		/>
	</>
);
