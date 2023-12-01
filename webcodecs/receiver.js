const readButton = document.getElementById('read');
const closeButton= document.getElementById('close');
const renderButton = document.getElementById('render');
const cnv = document.getElementById('dst');
const ctx = cnv.getContext("2d", {alpha: false});

const KEY_FRAME_SIZE = 5;
const HEADER_LENGTH = 28;
const PRE_SIGNAL = 0xFFFFFFFF;
const CHANEL = 1;

const config = {
  codec: 'avc1.42002A',
  avc: {format: 'annexb'},
  width: '640',
  height: '480',
  bitrate: 500_000,
  framerate: 25,
}

let transport, bdsReadable, bdsWritable;

const highestBit = 0b10000000;
let timeBase = 0;
let underflow = true;
let readLoop = true;
let readFrames = []

let videoDecoder = new VideoDecoder({
  output: (frame) => {
    readFrames.push(frame);
  },
  error: (error) => {
    console.log(error)
  }
})

videoDecoder.configure(config)


function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

function checkFirstFourBytes(data) {
  for (let i = 0; i < 4; i++)
    if (data[i] !== 0xFF) return false
  return true
}

function unpackFrame(data) {
  let dataView = new DataView(data.buffer, data.byteOffset, data.byteLength);
  let timestamp = Number(dataView.getBigUint64(20, false));
  console.log(timestamp)
  let chunkData = data.slice(28);
  let key = data[12] & highestBit;
  return {
    timestamp,
    chunkData,
    key: key ? "key" : "delta"
  }
}

function concatenateUint8Arrays(array1, array2) {
    let result = new Uint8Array(array1.length + array2.length);
    result.set(array1, 0);
    result.set(array2, array1.length);
    return result;
}

function calculateTimeTillNextFrame(timestamp) {
  if (timeBase === 0) timeBase = performance.now();
  const media_time = performance.now() - timeBase;
  return Math.max(0, timestamp - media_time);
}

async function renderFrame() {
  console.log('rendering...')
  if (readFrames.length === 0) {
    setTimeout(renderFrame, 2000);
  }
  const frame = readFrames.shift();
  // 根据帧的时间戳，计算在显示下一帧之前需要的实时等待时间
  console.log(readFrames.length)
  await sleep(400);
  ctx.drawImage(frame, 0, 0);
  frame.close();

  // 立即下一帧渲染
  setTimeout(renderFrame, 0);
}

async function read() {
  let frame = undefined

  transport = new WebTransport('https://www.localtest.com:4433/wt/test/get');
  await transport.ready;
  console.log('WebTransport Created.')

  let bds = await transport.createBidirectionalStream();
  let writer = bds.writable.getWriter();
  let reader = bds.readable.getReader();
  let data = new Uint8Array(4).fill(0xFF);
  await writer.write(data);
  console.log('write done. receiving...')
  while (readLoop) {
    const {value, done} = await reader.read();
    if (done) break;
    if (checkFirstFourBytes(value)) {
      if (frame !== undefined) {
        let {timestamp, chunkData} = unpackFrame(frame);
        let encodedVideoChunk = new EncodedVideoChunk({
          type: "key",
          duration: 0,
          timestamp: timestamp,
          data: chunkData
        })
        console.log(videoDecoder.state)
        try {
          if (videoDecoder.decodeQueueSize >= 5) {
            videoDecoder.reset();
            videoDecoder.configure(config)
          }
          videoDecoder.decode(encodedVideoChunk);
        } catch (e) {
          videoDecoder.reset();
          videoDecoder.configure(config)
        }
      }
      frame = value
    } else {
      frame = concatenateUint8Arrays(frame, value)
    }
  }
  console.log('exiting receive.')
}


async function close() {
  readLoop = false;
}

async function test() {
  const writableStream = new WritableStream({
    async write(chunk){
      console.log(chunk)
    }
  })
  console.log('ah oh')
  await bdsReadable.pipeTo(writableStream);
}


readButton.addEventListener('click', read);
closeButton.addEventListener('click', close);
renderButton.addEventListener('click', renderFrame);
// testButton.addEventListener('click', startWebTransport);

