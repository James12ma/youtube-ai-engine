import {Config} from '@remotion/cli/config';

Config.setVideoImageFormat('jpeg');
Config.setJpegQuality(95);
Config.setCodec('h264');
Config.setCrf(16);
Config.setPixelFormat('yuv420p');
// Tag + convert to broadcast BT.709 limited range (otherwise JPEG frames yield full-range yuvj420p).
Config.setColorSpace('bt709');
Config.setConcurrency(2);
Config.setOverwriteOutput(true);
