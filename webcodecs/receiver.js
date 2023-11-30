const readButton = document.getElementById('read')
const closeButton= document.getElementById('close');

const KEY_FRAME_SIZE = 5;
const HEADER_LENGTH = 28;
const PRE_SIGNAL = 0xFFFFFFFF;
const CHANEL = 1;

let transport
transport = new WebTransport('https://www.localtest.com:4433/wt/get');

async function readData(receiveFrame) {
  const reader = receiveFrame.getReader();
  while (true) {
    const {done, value} = await reader.read();
    if (done) break;
    console.log(value);
  }
}

async function read() {
  await transport.ready;
  console.log('WebTransport Created.')

  const uds = transport.incomingUnidirectionalStreams;
  const reader = uds.getReader();
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    await readData(value);
  }

}

async function close() {
  if (transport !== null) {
    transport.close()
    transport.closed
  }
}

readButton.addEventListener('click', read);
closeButton.addEventListener('click', close);

