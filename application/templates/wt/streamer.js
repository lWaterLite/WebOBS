const KEY_FRAME_SIZE = 5;
const HEADER_LENGTH = 28;
const PRE_SIGNAL = 0xFFFFFFFF;
const CHANEL = 1;
const CONFIG = {
  codec: 'avc1.42002A',
  avc: {format: 'annexb'},
  width: '640',
  height: '480',
  bitrate: 500_000,
  framerate: 25,
}

const startButton = document.getElementById('start')
const stopButton = document.getElementById('stop')

stopButton.disabled = true;

const url = 'https://www.localtest.com:4433/wt/push';

let transport, encoder;

function writeUint32(arr, pos, val) {
  let view = new DataView(arr)
  view.setUint32(pos, val, false)
}

function writeUint64(arr, pos, val) {
  let view = new DataView(arr)
  view.setBigUint64(pos, val, false)
}

async function sendVideoStream() {
  transport = new WebTransport(url);
  await transport.ready;
  stopButton.disabled = false;
  console.log('WebTransport Completed.')

  let captureStream = await navigator.mediaDevices.getDisplayMedia();
  let [videoTrack] = captureStream.getVideoTracks();
  let processor = new MediaStreamTrackProcessor(videoTrack);
  let inputStream = processor.readable;

  let frameCount = 0;

  const transformStream = new TransformStream({
    async start(controller) {
      encoder = new VideoEncoder({
        output: (chunk) => {
          let header = new ArrayBuffer(HEADER_LENGTH);
          let link_id = CHANEL;
          let length = (chunk.byteLength + 28) & 0xFFFFFFFF;
          let frameType = (chunk.type === 'key' ? 128 : 0);
          frameType = (frameType & 0xFF) << 24;
          let seqNumber = frameCount & 0xFFFFFFFF;
          let timestamp = chunk.timestamp;

          writeUint32(header, 0, PRE_SIGNAL);
          writeUint32(header, 4, link_id);
          writeUint32(header, 8, length);
          writeUint32(header, 12, frameType);
          writeUint32(header, 16, seqNumber);
          writeUint64(header, 20, BigInt(timestamp));

          let chunkBuffer = new ArrayBuffer(chunk.byteLength);
          chunk.copyTo(chunkBuffer);
          let data = new Uint8Array(chunk.byteLength + HEADER_LENGTH);
          data.set(new Uint8Array(header), 0);
          data.set(new Uint8Array(chunkBuffer), HEADER_LENGTH);

          controller.enqueue(data.buffer);
        },
        error: err => {
          console.log(err);
        }
      })
      encoder.configure(CONFIG);
    },
    async transform(frame) {
      frameCount++;
      encoder.encode(frame, {keyFrame: frameCount % KEY_FRAME_SIZE === 0})
      frame.close();
    }
  })

  const writableStream = new WritableStream({
    async write(chunk) {
      let uds = await transport.createUnidirectionalStream();
      let writer = uds.getWriter(); // MDN is wrong here, uds is already a writable.
      await writer.ready;
      await writer.write(chunk);
      await writer.abort();
    }
  })

  await inputStream.pipeThrough(transformStream).pipeTo(writableStream);
}

function stopVideoStream() {
  transport.close();
}

startButton.addEventListener('click', sendVideoStream);
stopButton.addEventListener('click', stopVideoStream);
