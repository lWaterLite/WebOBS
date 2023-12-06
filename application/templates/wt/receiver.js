const receiveButton = document.getElementById('receive');
const stopButton= document.getElementById('stop');
const renderButton = document.getElementById('render');
const cnv = document.getElementById('dst');
const ctx = cnv.getContext("2d", {alpha: false});

renderButton.disabled = true;
stopButton.disabled = true;

const CONFIG = {
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

videoDecoder.configure(CONFIG)


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

async function renderFrame() {
  console.log('rendering...')
  if (readFrames.length === 0) {
    setTimeout(renderFrame, 2000);
  }
  const frame = readFrames.shift();
  await sleep(40);
  ctx.drawImage(frame, 0, 0);
  frame.close();

  // 立即下一帧渲染
  setTimeout(renderFrame, 0);
}

async function startReceive() {
  let frame = undefined

  transport = new WebTransport('https://www.localtest.com:4433/wt/get');
  await transport.ready;
  console.log('WebTransport Created.')

  stopButton.disabled = false;
  renderButton.disabled = false;

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
            videoDecoder.configure(CONFIG)
          }
          videoDecoder.decode(encodedVideoChunk);
        } catch (e) {
          videoDecoder.reset();
          videoDecoder.configure(CONFIG)
        }
      }
      frame = value
    } else {
      frame = concatenateUint8Arrays(frame, value)
    }
  }
  console.log('exiting receive.')
}


async function stopReceive() {
  readLoop = false;
  await transport.close()
}

receiveButton.addEventListener('click', startReceive);
stopButton.addEventListener('click', stopReceive);
renderButton.addEventListener('click', renderFrame);

