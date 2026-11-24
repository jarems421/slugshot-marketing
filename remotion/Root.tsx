import React from 'react';
import {Composition} from 'remotion';
import {Vertical, VerticalProps} from './Vertical';

const FPS = 30;

// Defaults point at the smoke-test sample that `ss.ps1 render` copies into public/sample/.
const defaultProps: VerticalProps = {
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
};

export const RemotionRoot: React.FC = () => (
	<Composition
		id="Vertical"
		component={Vertical}
		width={1080}
		height={1920}
		fps={FPS}
		durationInFrames={FPS * 12}
		defaultProps={defaultProps}
		calculateMetadata={({props}) => ({
			durationInFrames: Math.ceil(
				FPS * (props.clipSeconds + (props.endCard ? props.endCardSeconds : 0)),
			),
		})}
	/>
);
