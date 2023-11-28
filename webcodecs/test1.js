async function createWebTransportStream(url) {
  transport = new WebTransport(url);
  await transport.ready;
  let transportStream = await transport.createBidirectionalStream();
  return {'readable': transportStream.readable, 'writable': transportStream.writable}
}

const KEY_FRAME_SIZE = 5;
const HEADER_LENGTH = 28;
const PRE_SIGNAL = 0xFFFFFFFF;
const CHANEL = 1;

const displayVideo = document.getElementById('display');
const startButton = document.getElementById('start');
const stopButton = document.getElementById('stop');
const testButton = document.getElementById('test');
const readButton = document.getElementById('read');
const readStopButton = document.getElementById('r_stop');


stopButton.disabled = true;

const config = {
  codec: 'avc1.42002A',
  avc: {format: 'annexb'},
  width: '1600',
  height: '900',
  bitrate: 2_000_000,
  framerate: 30,
}

let inputStream, outputStream, encoder, decoder, readStream, writeStream, transport;

const generator = new MediaStreamTrackGenerator({kind: 'video'});
outputStream = generator.writable;
displayVideo.srcObject = new MediaStream([generator]);

createWebTransportStream('https://www.localtest.com:4433/wt/push').then(res => {
  readStream = res.readable;
  writeStream = res.writable;
  console.log('WebTransport Created.');
})

/*
Header format (28 bytes):
                     1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
|                         pre-signal                            |
-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
|                         link   id                             |
-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
|                        chunk length                           |
-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
|T                                                              |
-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
|                          seq number                           |
-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
|                          timestamp...                         |
-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
|                          timestamp                            |
-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
                           payload...
 */

/*
Chunk length include header length

Pre-signal loads are set to FFFFFFFF, to inform the server that a chunk head is coming.

T: frame type
  key frame = 1
  delta frame = 0
 */

function writeUint32(arr, pos, val) {
  let view = new DataView(arr)
  view.setUint32(pos, val, false)
}

function writeUint64(arr, pos, val) {
  let view = new DataView(arr)
  view.setBigUint64(pos, val, false)
}


class VideoStreamFactory {

  inputStream;
  outputStream;
  config;

  constructor(streamData) {
    this.inputStream = streamData.inputStream;
    this.outputStream = streamData.outputStream;
    this.config = streamData.config;
  }

  setInputStream(inputSteam) {
    this.inputStream = inputSteam;
  }

  // encodeVideoStream() {
  //   let frameCount = 0;
  //   let that = this
  //   return new TransformStream({
  //     async start(controller) {
  //       this.encoder = encoder = new VideoEncoder({
  //         output: (chunk, metadata) => {
  //           console.log(chunk);
  //           let buffer = new ArrayBuffer(chunk.byteLength);
  //           chunk.copyTo(buffer);
  //           console.log(buffer)
  //           controller.enqueue(buffer);
  //         },
  //         error: err => {
  //           console.log(err)
  //         }
  //       })
  //       this.encoder.configure(that.config);
  //     },
  //     transform(frame) {
  //       frameCount++;
  //       this.encoder.encode(frame, {keyFrame: frameCount % KEY_FRAME_SIZE === 0})
  //       frame.close()
  //     }
  //   })
  // }

  encodeVideoStream() {
    let frameCount = 0;
    let that = this
    return new TransformStream({
      async start(controller) {
        this.encoder = encoder = new VideoEncoder({
          output: (chunk, metadata) => {
            frameCount++;
            let header = new ArrayBuffer(HEADER_LENGTH)
            let link_id = CHANEL;
            let length = (chunk.byteLength+28) & 0xFFFFFFFF;
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

            console.log(data);
            // controller.enqueue(data.buffer);

            let uniDirectStream = transport.createUnidirectionalStream();
            let writer = uniDirectStream.getWriter(); // MDN IS WRONG!!!
            writer.write(data);
          },
          error: (error) => {
            console.log(error);
          }
        })
        this.encoder.configure(that.config);
      },
      transform(frame, controller) {
        frameCount++;
        this.encoder.encode(frame, {keyFrame: frameCount % KEY_FRAME_SIZE === 0})
        frame.close();
      }
    })
  }

  decodeVideoStream() {
    let that = this
    return new TransformStream({
      start(controller) {
        this.decoder = decoder = new VideoDecoder({
          output: (frame) => {
            controller.enqueue(frame)
          },
          error: (error) => {
            console.log(error)
          }
        })
        this.decoder.configure(that.config)
      },
      async transform(chunk, controller) {
        this.decoder.decode(chunk);
      }
    })
  }

  async Start() {
    testButton.disabled = true;
    stopButton.disabled = false;
    await this.inputStream.pipeThrough(this.encodeVideoStream())
  }

  Stop() {
    this.inputStream.cancel();
    encoder.close();
    displayVideo.srcObject = null;
  }

}

const videoStreamFactory = new VideoStreamFactory({inputStream, outputStream, config})


async function main() {
  let captureStream = await navigator.mediaDevices.getDisplayMedia();
  displayVideo.srcObject = captureStream;
  let videoTrack = captureStream.getVideoTracks()[0];
  let processor = new MediaStreamTrackProcessor(videoTrack);
  console.log(processor);

}

async function test() {
  let captureStream = await navigator.mediaDevices.getDisplayMedia();
  let [videoTrack] = captureStream.getVideoTracks();
  let processor = new MediaStreamTrackProcessor(videoTrack);
  videoStreamFactory.setInputStream(processor.readable)
  await videoStreamFactory.Start();
  // console.log(processor);
  // console.log(frame)
}

let read_stream = true;


startButton.onclick = () => {
  main();
}

function getRandomInt(min, max) {
  min = Math.ceil(min); // 向上取整
  max = Math.floor(max); // 向下取整
  return Math.floor(Math.random() * (max - min + 1)) + min;
}

async function sendPackets() {
  console.log('send start')
  const url = 'https://www.localtest.com:4433/wt/push'; // 替换为你的服务器地址
  const transport = new WebTransport(url);
  console.log(transport)

  try {
    await transport.ready; // 等待连接建立
    const header = new Uint8Array(28).fill(0xFF);
    setInterval(async () => {
      let bodyLength = getRandomInt(20, 50000);
      let body = new Uint8Array(bodyLength).fill(0x77); // 创建并填充数据
      let data = new Uint8Array(bodyLength+28);
      data.set(header, 0);
      data.set(body, 28);
      console.log(data)
      let transportStream = await transport.createUnidirectionalStream();
      let writer = transportStream.getWriter(); // 获取写入器
      await writer.write(data); // 发送数据
    }, 1000); // 每隔 1 秒

  } catch (error) {
    console.error('连接失败:', error);
  }
}

testButton.addEventListener('click', test)
stopButton.addEventListener('click', () => {
  videoStreamFactory.Stop();
})

