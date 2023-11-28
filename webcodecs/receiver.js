const readButton = document.getElementById('read')
const closeButton= document.getElementById('close');

const KEY_FRAME_SIZE = 5;
const HEADER_LENGTH = 28;
const PRE_SIGNAL = 0xFFFFFFFF;
const CHANEL = 1;

let webtransport2;
let wtClosed = false;
function writeUint32(arr, pos, val) {
  let view = new DataView(arr)
  view.setUint32(pos, val, false)
}

let read_stream = true;
async function read() {
  webtransport2 = new WebTransport('https://www.localtest.com:4433/wt/test/get');
  await webtransport2.ready;
  console.log('WebTransport Created.')
  let transportStream2 = await webtransport2.createBidirectionalStream();
  let writer = transportStream2.writable.getWriter();
  let informer = new ArrayBuffer(4);
  writeUint32(informer, 0, CHANEL);
  await writer.write(informer)
  let reader = transportStream2.readable.getReader();
  let count = 0
  while (read_stream && !wtClosed) {
    let receive = await reader.read();
    if (receive.value === undefined) {
      count++
    }
    if (count === 10) {
      read_stream = false;
    }
    console.log(receive)
  }
}

async function close() {
  if (webtransport2 !== null) {
    webtransport2.close()
    webtransport2.closed.then(() => {
      wtClosed = true;
    })
  }
}

readButton.addEventListener('click', read);
closeButton.addEventListener('click', close);

